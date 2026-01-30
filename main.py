import os, sqlite3, telebot, time
from telebot import types
from flask import Flask
from threading import Thread

# --- CONFIG ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208
CHANNELS = ["@anonymousely", "@anonymouslyrobott"]
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# --- DB SETUP ---
def init_db():
    conn = sqlite3.connect('anonymous_pro.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER UNIQUE, name TEXT, 
                  loc TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 5, 
                  refs INTEGER DEFAULT 0, partner INTEGER DEFAULT 0, lang TEXT DEFAULT 'am')''')
    conn.commit()
    return conn

db = init_db()
user_steps = {}

# --- TEXTS ---
TEXTS = {
    'am': {
        'start': "👋 እንኳን ደህና መጡ! ቦቱን ለመጠቀም መጀመሪያ ይመዝገቡ።\n\nእባክዎ ስምዎን ያስገቡ ✍️:",
        'loc': "📍 መኖሪያ ቦታዎ የት ነው?",
        'age': "🎂 እድሜዎን ያስገቡ (በቁጥር ብቻ 🔢):",
        'gender': "🚻 ጾታዎን ይምረጡ:",
        'join': "⚠️ ቦቱን ለመቀጠል መጀመሪያ ቻናሎቻችንን መቀላቀል አለብዎት:\n1️⃣ {ch1}\n2️⃣ {ch2}",
        'main': "🏠 ዋና ማውጫ",
        'search': "🔍 ሸሪክ በመፈለግ ላይ...",
        'found': "⚡ ተገናኝተዋል! አሪፍ ቆይታ ይሁንላችሁ 👋😊",
        'stop': "❌ ቻት ተቋርጧል። ፓርትነርዎን ደረጃ ይስጡ 👇:",
        'heart_err': "❌ Reply ለመጻፍ ቢያንስ 37 ❤️ ያስፈልግዎታል! 💔"
    },
    'en': {
        'start': "👋 Welcome! Please register first to use the bot.\n\nEnter your name ✍️:",
        'loc': "📍 Where do you live?",
        'age': "🎂 Enter your age (numbers only 🔢):",
        'gender': "🚻 Select your gender:",
        'join': "⚠️ You must join our channels first:\n1️⃣ {ch1}\n2️⃣ {ch2}",
        'main': "🏠 Main Menu",
        'search': "🔍 Searching for a partner...",
        'found': "⚡ Connected! Have a great chat 👋😊",
        'stop': "❌ Chat ended. Rate your partner 👇:",
        'heart_err': "❌ You need at least 37 ❤️ to reply! 💔"
    }
}

# --- HELPERS ---
def is_joined(uid):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status == 'left': return False
        except: return False
    return True

def get_user(uid):
    return db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()

# --- REGISTRATION ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    u = get_user(uid)
    
    if not u:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Amharic 🇪🇹", callback_data="l_am"),
                   types.InlineKeyboardButton("English 🇺🇸", callback_data="l_en"))
        bot.send_message(uid, "🌍 Select Language / ቋንቋ ይምረጡ:", reply_markup=markup)
        ref = m.text.split()[1] if len(m.text.split()) > 1 else None
        user_steps[uid] = {'step': 'lang', 'ref': ref}
    else:
        if not is_joined(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check / ቸክ አድርግ", callback_data="check"))
            return bot.send_message(uid, TEXTS[u[9]]['join'].format(ch1=CHANNELS[0], ch2=CHANNELS[1]), reply_markup=markup)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⚡ Find a partner 🔍", "💎 Premium Search ✨")
        markup.row("👤 My Profile 📝", "⚙️ Settings ⚙️")
        bot.send_message(uid, TEXTS[u[9]]['main'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('l_'))
def set_lang(call):
    uid = call.from_user.id
    lang = call.data.split('_')[1]
    user_steps[uid].update({'lang': lang, 'step': 'name'})
    bot.edit_message_text(TEXTS[lang]['start'], uid, call.message.message_id)

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def reg_process(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']
    lang = user_steps[uid].get('lang', 'am')
    
    if step == 'name':
        if len(m.text) < 3: return bot.send_message(uid, "❌")
        user_steps[uid].update({'name': m.text, 'step': 'loc'})
        bot.send_message(uid, TEXTS[lang]['loc'])
    elif step == 'loc':
        user_steps[uid].update({'loc': m.text, 'step': 'age'})
        bot.send_message(uid, TEXTS[lang]['age'])
    elif step == 'age':
        if not m.text.isdigit(): return bot.send_message(uid, "🔢")
        user_steps[uid].update({'age': int(m.text), 'step': 'gender'})
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Male 👨", "Female 👩")
        bot.send_message(uid, TEXTS[lang]['gender'], reply_markup=markup)
    elif step == 'gender':
        d = user_steps[uid]
        db.execute("INSERT INTO users (uid, name, loc, age, gender, lang) VALUES (?,?,?,?,?,?)", 
                   (uid, d['name'], d['loc'], d['age'], m.text, d['lang']))
        if d['ref']:
            rid = int(d['ref'])
            db.execute("UPDATE users SET refs = refs + 1 WHERE uid=?", (rid,))
            refs = db.execute("SELECT refs FROM users WHERE uid=?", (rid,)).fetchone()[0]
            if refs % 2 == 0:
                db.execute("UPDATE users SET hearts = hearts + 1 WHERE uid=?", (rid,))
                try: bot.send_message(rid, "❤️ 1 Heart Earned! 🎉")
                except: pass
        db.commit()
        bot.send_message(ADMIN_ID, f"🆕 New User Registered!\nID: <code>{uid}</code>")
        del user_steps[uid]
        bot.send_message(uid, "✅ Success! /start")

# --- CHAT & MEDIA RELAY ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice', 'animation', 'video_note', 'sticker'])
def handle_all(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u: return
    
    lang = u[9]

    if m.reply_to_message and u[6] < 37:
        return bot.send_message(uid, TEXTS[lang]['heart_err'])

    if m.text == "⚡ Find a partner 🔍":
        if u[8] != 0: return bot.send_message(uid, "⚠️ /stop first!")
        bot.send_message(uid, TEXTS[lang]['search'])
        p = db.execute("SELECT uid FROM users WHERE uid!=? AND partner=0 ORDER BY RANDOM() LIMIT 1", (uid,)).fetchone()
        if p:
            pid = p[0]
            db.execute("UPDATE users SET partner=? WHERE uid=?", (pid, uid))
            db.execute("UPDATE users SET partner=? WHERE uid=?", (uid, pid))
            db.commit()
            bot.send_message(uid, TEXTS[lang]['found'])
            bot.send_message(pid, TEXTS[lang]['found'])
        else: bot.send_message(uid, "⏳ No one found.")

    elif m.text == "💎 Premium Search ✨":
        bot.send_message(uid, "💎 Premium Search costs 1 ❤️ or Stars.\nSelect Gender:", reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("Female 👩", callback_data="ps_Female"),
            types.InlineKeyboardButton("Male 👨", callback_data="ps_Male")
        ))

    elif m.text == "👤 My Profile 📝":
        link = f"t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(uid, f"👤 <b>Profile</b>\n\n❤️ Hearts: {u[6]}\n🔗 Share Link: <code>{link}</code>")

    elif u[8] != 0:
        try: bot.copy_message(u[8], uid, m.message_id)
        except: bot.send_message(uid, "❌ Failed to deliver.")

@bot.message_handler(commands=['stop'])
def stop_chat(m):
    uid = m.from_user.id
    u = get_user(uid)
    if u and u[8] != 0:
        pid = u[8]
        db.execute("UPDATE users SET partner=0 WHERE uid IN (?,?)", (uid, pid))
        db.commit()
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("👍", callback_data="r"), types.InlineKeyboardButton("👎", callback_data="r"))
        bot.send_message(uid, TEXTS[u[9]]['stop'], reply_markup=markup)
        bot.send_message(pid, TEXTS[get_user(pid)[9]]['stop'], reply_markup=markup)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['ping'])
def ping(m):
    if m.from_user.id != ADMIN_ID: return
    msg = m.text.replace("/ping ", "")
    users = db.execute("SELECT uid FROM users").fetchall()
    for u in users:
        try: bot.send_message(u[0], f"📢 {msg} 🔔")
        except: pass

@bot.message_handler(commands=['info13'])
def info13(m):
    if m.from_user.id != ADMIN_ID: return
    res = db.execute("SELECT id, name FROM users LIMIT 50").fetchall()
    txt = "📋 <b>Users:</b>\n" + "\n".join([f"{r[0]}. {r[1]}" for r in res])
    bot.send_message(ADMIN_ID, txt)

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message)
def admin_reply(m):
    if m.text.isdigit():
        u = db.execute("SELECT * FROM users WHERE id=?", (int(m.text),)).fetchone()
        if u:
            bot.send_message(ADMIN_ID, f"👤 Info:\nID: {u[1]}\nName: {u[2]}\nLoc: {u[3]}\nGender: {u[4]}\nAge: {u[5]}\n❤️: {u[6]}")

# --- SERVER ---
@app.route('/')
def home(): return "Bot Active"
def run(): bot.infinity_polling()
if __name__ == "__main__":
    Thread(target=run).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
