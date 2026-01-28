import os, sqlite3, telebot, time
from telebot import types
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208
CHANNELS = ["@anonymousely", "@anonymouslyrobott"]
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('pro_bot.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER UNIQUE, name TEXT, 
                  loc TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 5, 
                  refs INTEGER DEFAULT 0, partner INTEGER DEFAULT 0, lang TEXT DEFAULT 'am')''')
    conn.commit()
    return conn

db = init_db()
user_steps = {}

# --- HELPERS ---
def is_joined(uid):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status == 'left': return False
        except: return False
    return True

# --- REGISTRATION ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = m.from_user.id
    u = db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
    
    if not u:
        bot.send_message(uid, "👋 እንኳን ደህና መጡ! ለመመዝገብ መጀመሪያ ስምዎን ያስገቡ (ቢያንስ 3 ፊደል):")
        ref = m.text.split()[1] if len(m.text.split()) > 1 else None
        user_steps[uid] = {'step': 'name', 'ref': ref}
    else:
        if not is_joined(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check Joining", callback_data="check"))
            msg = f"⚠️ ቦቱን ለመጠቀም መጀመሪያ ቻናሎቻችንን መቀላቀል አለብዎት:\n\n1. {CHANNELS[0]}\n2. {CHANNELS[1]}"
            return bot.send_message(uid, msg, reply_markup=markup)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⚡ Find a partner 🔍", "💎 Premium Search ✨")
        markup.row("👤 My Profile 📝", "⚙️ Settings ⚙️")
        bot.send_message(uid, "🏠 Main Menu", reply_markup=markup)

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def handle_reg(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']
    
    if step == 'name':
        if len(m.text) < 3: return bot.send_message(uid, "❌ ስም በጣም አጭር ነው፣ እባክዎ በድጋሚ ያስገቡ 🔡:")
        user_steps[uid].update({'name': m.text, 'step': 'loc'})
        bot.send_message(uid, "📍 መኖሪያ ቦታዎን ያስገቡ:")
    elif step == 'loc':
        user_steps[uid].update({'loc': m.text, 'step': 'age'})
        bot.send_message(uid, "🎂 እድሜዎን ያስገቡ (ቁጥር ብቻ 🔢):")
    elif step == 'age':
        if not m.text.isdigit(): return bot.send_message(uid, "🔢 እባክዎ ቁጥር ብቻ ያስገቡ:")
        user_steps[uid].update({'age': int(m.text), 'step': 'gender'})
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Male 👨", "Female 👩")
        bot.send_message(uid, "🚻 ጾታዎን ይምረጡ:", reply_markup=markup)
    elif step == 'gender':
        d = user_steps[uid]
        db.execute("INSERT INTO users (uid, name, loc, age, gender) VALUES (?,?,?,?,?)", (uid, d['name'], d['loc'], d['age'], m.text))
        if d['ref']:
            rid = int(d['ref'])
            db.execute("UPDATE users SET refs = refs + 1 WHERE uid=?", (rid,))
            refs = db.execute("SELECT refs FROM users WHERE uid=?", (rid,)).fetchone()[0]
            if refs % 2 == 0:
                db.execute("UPDATE users SET hearts = hearts + 1 WHERE uid=?", (rid,))
                try: bot.send_message(rid, "❤️ 2 ሰው ስለጋበዙ 1 ልብ ተሰጥቶዎታል! 🎉")
                except: pass
        db.commit()
        bot.send_message(ADMIN_ID, f"🆕 አዲስ ተመዝጋቢ ተገኝቷል ✅\n\n👤 ስም: {d['name']}\n🆔 ID: <code>{uid}</code>")
        del user_steps[uid]
        bot.send_message(uid, "✅ ምዝገባ ተጠናቋል። አሁን /start ብለው ቦቱን መጠቀም ይችላሉ። 🚀")

# --- CHAT RELAY ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice', 'animation'])
def chat_relay(m):
    uid = m.from_user.id
    u = db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
    if not u: return

    # Heart limit for replay (Req 15)
    if m.reply_to_message and u[6] < 37:
        return bot.send_message(uid, "❌ Reply ለመጻፍ ቢያንስ 37 ❤️ ያስፈልግዎታል! 💔")

    if m.text == "⚡ Find a partner 🔍":
        if u[8] != 0: return bot.send_message(uid, "⚠️ መጀመሪያ ካሉበት ቻት ለመውጣት /stop ይበሉ። 🛑")
        bot.send_message(uid, "🔍 ሰው በመፈለግ ላይ... እባክዎ ይጠብቁ ⏳")
        p = db.execute("SELECT uid FROM users WHERE uid!=? AND partner=0 ORDER BY RANDOM() LIMIT 1", (uid,)).fetchone()
        if p:
            db.execute("UPDATE users SET partner=? WHERE uid=?", (p[0], uid))
            db.execute("UPDATE users SET partner=? WHERE uid=?", (uid, p[0]))
            db.commit()
            bot.send_message(uid, "⚡ ተገናኝተዋል! አሪፍ ቆይታ ይሁንላችሁ 👋😊")
            bot.send_message(p[0], "⚡ ተገናኝተዋል! አሪፍ ቆይታ ይሁንላችሁ 👋😊")
        else: bot.send_message(uid, "⏳ በአሁኑ ሰዓት ሰው አልተገኘም፣ እባክዎ ጥቂት ቆይተው ይሞክሩ። 🔄")
    
    elif m.text == "👤 My Profile 📝":
        link = f"t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid, f"👤 <b>የእርስዎ መረጃ</b>\n\n👤 ስም: {u[2]}\n📍 ቦታ: {u[3]}\n❤️ ልብ: {u[6]}\n🔗 መጋበዣ ሊንክ: <code>{link}</code>\n\nለ 2 ሰው ሲያጋሩ 1 ❤️ ያገኛሉ! 🎁")

    elif u[8] != 0:
        try: bot.copy_message(u[8], uid, m.message_id)
        except: bot.send_message(uid, "❌ መልእክቱ አልደረሰም፣ ፓርትነርዎ ሳይወጣ አልቀረም 🛑")

@bot.message_handler(commands=['stop'])
def stop_chat(m):
    u = db.execute("SELECT * FROM users WHERE uid=?", (m.from_user.id,)).fetchone()
    if u and u[8] != 0:
        pid = u[8]
        db.execute("UPDATE users SET partner=0 WHERE uid IN (?,?)", (m.from_user.id, pid))
        db.commit()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👍", callback_data="r"), types.InlineKeyboardButton("👎", callback_data="r"))
        bot.send_message(m.from_user.id, "❌ ቻት ተቋርጧል። ፓርትነርዎን ደረጃ ይስጡ 👇:", reply_markup=markup)
        bot.send_message(pid, "❌ ቻት ተቋርጧል። ፓርትነርዎን ደረጃ ይስጡ 👇:", reply_markup=markup)
    else: bot.send_message(m.from_user.id, "❌ አሁን ላይ ከማንም ጋር አልተገናኙም 🤷‍♂️")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['ping'])
def admin_ping(m):
    if m.from_user.id != ADMIN_ID: return
    msg = m.text.replace("/ping ", "")
    users = db.execute("SELECT uid FROM users").fetchall()
    for u in users:
        try: bot.send_message(u[0], f"📢 <b>የአድሚን መልእክት:</b>\n\n{msg} 🔔")
        except: pass
    bot.reply_to(m, "✅ መልእክቱ ለሁሉም ተልኳል!")

@bot.message_handler(commands=['info13'])
def admin_info(m):
    if m.from_user.id != ADMIN_ID: return
    res = db.execute("SELECT id, name FROM users LIMIT 50").fetchall()
    txt = "📋 <b>የተመዘገቡ ሰዎች:</b>\n" + "\n".join([f"{r[0]}. {r[1]}" for r in res])
    bot.send_message(ADMIN_ID, txt + "\n\nለዝርዝር መረጃ ቁጥሩን ሪፕላይ (Reply) አድርገው ይላኩ።")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message)
def admin_detail(m):
    if m.text.isdigit():
        u = db.execute("SELECT * FROM users WHERE id=?", (int(m.text),)).fetchone()
        if u:
            info = f"👤 መረጃ:\n\nID: <code>{u[1]}</code>\nስም: {u[2]}\nቦታ: {u[3]}\nጾታ: {u[4]}\nእድሜ: {u[5]}\n❤️ ልብ: {u[6]}"
            bot.send_message(ADMIN_ID, info)

# --- WEB SERVER ---
@app.route('/')
def index(): return "Bot is running! 🚀"
def run_bot(): bot.infinity_polling()

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
