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
    conn = sqlite3.connect('pro_bot.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER UNIQUE, name TEXT, 
                  loc TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 5, 
                  refs INTEGER DEFAULT 0, partner INTEGER DEFAULT 0, lang TEXT)''')
    conn.commit()
    conn.close()

init_db()
user_steps = {}

# --- HELPERS ---
def is_joined(uid):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status == 'left': return False
        except: return False
    return True

def get_user(uid):
    conn = sqlite3.connect('pro_bot.db')
    u = conn.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()
    conn.close()
    return u

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚡ Find a partner", "💎 Premium Search")
    markup.row("👤 My Profile", "⚙️ Settings")
    return markup

# --- START & REG ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u:
        bot.send_message(uid, "👋 Welcome! Please enter your name (min 3 letters):")
        ref = m.text.split()[1] if len(m.text.split()) > 1 else None
        user_steps[uid] = {'step': 'name', 'ref': ref}
    else:
        if not is_joined(uid):
            msg = f"⚠️ Please join our channels first:\n1. {CHANNELS[0]}\n2. {CHANNELS[1]}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check", callback_data="check"))
            return bot.send_message(uid, msg, reply_markup=markup)
        bot.send_message(uid, "🏠 Main Menu", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def reg(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']
    if step == 'name':
        if len(m.text) < 3: bot.send_message(uid, "❌ Too short! Try again:")
        else:
            user_steps[uid].update({'name': m.text, 'step': 'loc'})
            bot.send_message(uid, "📍 Enter your location:")
    elif step == 'loc':
        user_steps[uid].update({'loc': m.text, 'step': 'age'})
        bot.send_message(uid, "🎂 Enter your age (number only):")
    elif step == 'age':
        if not m.text.isdigit(): bot.send_message(uid, "🔢 Numbers only:")
        else:
            user_steps[uid].update({'age': int(m.text), 'step': 'gender'})
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("Male 👨", "Female 👩")
            bot.send_message(uid, "🚻 Select gender:", reply_markup=markup)
    elif step == 'gender':
        d = user_steps[uid]
        conn = sqlite3.connect('pro_bot.db')
        conn.execute("INSERT INTO users (uid, name, loc, age, gender) VALUES (?,?,?,?,?)",
                     (uid, d['name'], d['loc'], d['age'], m.text))
        if d['ref']:
            rid = int(d['ref'])
            conn.execute("UPDATE users SET refs = refs + 1 WHERE uid=?", (rid,))
            r = conn.execute("SELECT refs FROM users WHERE uid=?", (rid,)).fetchone()
            if r and r[0] % 2 == 0:
                conn.execute("UPDATE users SET hearts = hearts + 1 WHERE uid=?", (rid,))
                bot.send_message(rid, "❤️ You invited 2 people and earned 1 heart!")
        conn.commit()
        conn.close()
        bot.send_message(ADMIN_ID, f"🆕 New User: {d['name']} | ID: <code>{uid}</code>")
        del user_steps[uid]
        bot.send_message(uid, "✅ Registration complete! Use /start.")

# --- CHAT & ADMIN ---
@bot.message_handler(commands=['ping'])
def ping(m):
    if m.from_user.id != ADMIN_ID: return
    txt = m.text.replace("/ping ", "")
    conn = sqlite3.connect('pro_bot.db')
    users = conn.execute("SELECT uid FROM users").fetchall()
    for u in users:
        try: bot.send_message(u[0], f"📢 {txt}")
        except: pass
    bot.reply_to(m, "✅ Sent!")

@bot.message_handler(commands=['info13'])
def info13(m):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('pro_bot.db')
    users = conn.execute("SELECT id, name FROM users LIMIT 30").fetchall()
    res = "📋 User List:\n" + "\n".join([f"{u[0]}. {u[1]}" for u in users])
    bot.send_message(ADMIN_ID, res)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice', 'animation'])
def handle_all(m):
    uid = m.from_user.id
    u = get_user(uid)
    if not u: return
    
    if m.reply_to_message and u[6] < 37:
        return bot.send_message(uid, "❌ You need 37 ❤️ to reply!")

    if m.text == "⚡ Find a partner":
        if u[8] != 0: return bot.send_message(uid, "⚠️ Finish your chat first! Use /stop.")
        bot.send_message(uid, "🔍 Searching...")
        conn = sqlite3.connect('pro_bot.db')
        p = conn.execute("SELECT uid FROM users WHERE uid!=? AND partner=0 ORDER BY RANDOM() LIMIT 1", (uid,)).fetchone()
        if p:
            pid = p[0]
            conn.execute("UPDATE users SET partner=? WHERE uid=?", (pid, uid))
            conn.execute("UPDATE users SET partner=? WHERE uid=?", (uid, pid))
            conn.commit()
            bot.send_message(uid, "⚡ Connected! Say hi 👋")
            bot.send_message(pid, "⚡ Connected! Say hi 👋")
        else: bot.send_message(uid, "⏳ No one found. Try again.")
        conn.close()
    
    elif m.text == "👤 My Profile":
        bot.send_message(uid, f"👤 Name: {u[2]}\n❤️ Hearts: {u[6]}\n🔗 Link: <code>t.me/{bot.get_me().username}?start={uid}</code>")

    elif u[8] != 0:
        try: bot.copy_message(u[8], uid, m.message_id)
        except: bot.send_message(uid, "❌ Partner disconnected.")

@bot.message_handler(commands=['stop'])
def stop(m):
    u = get_user(m.from_user.id)
    if u and u[8] != 0:
        pid = u[8]
        conn = sqlite3.connect('pro_bot.db')
        conn.execute("UPDATE users SET partner=0 WHERE uid IN (?,?)", (m.from_user.id, pid))
        conn.commit()
        conn.close()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👍", callback_data="r"), types.InlineKeyboardButton("👎", callback_data="r"))
        bot.send_message(m.from_user.id, "❌ Chat ended. Rate:", reply_markup=markup)
        bot.send_message(pid, "❌ Chat ended. Rate:", reply_markup=markup)

# --- WEB SERVER ---
@app.route('/')
def h(): return "Bot Online"
def run(): bot.polling(none_stop=True)
if __name__ == "__main__":
    Thread(target=run).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
