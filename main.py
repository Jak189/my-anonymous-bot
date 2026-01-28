import os, sqlite3, telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208 
CHANNEL_ID = "@anonymousely" # Make sure the bot is admin here
CHANNEL_URL = "https://t.me/anonymousely"
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE SETUP ---
def get_db():
    conn = sqlite3.connect('anonymous_pro.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, name TEXT, 
                  location TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 5, 
                  referrals INTEGER DEFAULT 0, partner_id INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()
user_steps = {}

# --- UTILS ---
def is_joined(uid):
    try:
        status = bot.get_chat_member(CHANNEL_ID, uid).status
        return status in ['member', 'administrator', 'creator']
    except: return True

def get_user(uid):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return user

# --- MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚡ Find a partner", "💎 Premium Search")
    markup.row("👤 My Profile", "⚙️ Settings")
    return markup

# --- START & REGISTRATION ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        args = message.text.split()
        ref = args[1] if len(args) > 1 else None
        bot.send_message(uid, "👋 Welcome! Please enter your name:")
        user_steps[uid] = {'step': 'name', 'ref': ref}
    else:
        if not is_joined(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check Joining", callback_data="check_join"))
            return bot.send_message(uid, f"⚠️ You must join our channel first:\n{CHANNEL_URL}", reply_markup=markup)
        bot.send_message(uid, "🏠 Main Menu", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def reg_flow(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']
    
    if step == 'name':
        if len(m.text) < 3: bot.send_message(uid, "❌ Name too short. Try again:")
        else:
            user_steps[uid]['name'] = m.text
            user_steps[uid]['step'] = 'loc'
            bot.send_message(uid, "📍 Enter your location:")
    elif step == 'loc':
        user_steps[uid]['loc'] = m.text
        user_steps[uid]['step'] = 'age'
        bot.send_message(uid, "🎂 Enter your age:")
    elif step == 'age':
        if not m.text.isdigit(): bot.send_message(uid, "🔢 Numbers only please:")
        else:
            user_steps[uid]['age'] = int(m.text)
            user_steps[uid]['step'] = 'gender'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add("Male 👨", "Female 👩")
            bot.send_message(uid, "🚻 Select gender:", reply_markup=markup)
    elif step == 'gender':
        conn = get_db()
        conn.execute("INSERT INTO users (user_id, name, location, gender, age) VALUES (?,?,?,?,?)",
                     (uid, user_steps[uid]['name'], user_steps[uid]['loc'], m.text, user_steps[uid]['age']))
        # Referral bonus
        if user_steps[uid]['ref'] and user_steps[uid]['ref'].isdigit():
            rid = int(user_steps[uid]['ref'])
            conn.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (rid,))
            r_data = conn.execute("SELECT referrals FROM users WHERE user_id=?", (rid,)).fetchone()
            if r_data and r_data[0] % 2 == 0:
                conn.execute("UPDATE users SET hearts = hearts + 1 WHERE user_id=?", (rid,))
                bot.send_message(rid, "❤️ You earned 1 heart for 2 invites!")
        conn.commit()
        conn.close()
        bot.send_message(uid, f"✅ Registered! Now join: {CHANNEL_URL}")
        bot.send_message(ADMIN_ID, f"🆕 New: {user_steps[uid]['name']} | ID: `{uid}`", parse_mode="Markdown")
        del user_steps[uid]

# --- ADMIN BROADCAST ---
@bot.message_handler(commands=['ping'])
def ping(m):
    if m.from_user.id != ADMIN_ID: return
    msg = m.text.replace("/ping ", "")
    conn = get_db()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    for u in users:
        try: bot.send_message(u[0], f"📢 Update: {msg}")
        except: pass
    bot.reply_to(m, "✅ Broadcast sent.")

# --- FEATURES ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'audio', 'document', 'voice'])
def handle_all(m):
    uid = m.from_user.id
    user = get_user(uid)
    if not user: return
    
    # Check Hearts for reply (Requirement #15)
    if user[6] < 37 and m.reply_to_message:
        return bot.reply_to(m, "❌ You need at least 37 ❤️ to reply to messages.")

    if m.text == "⚡ Find a partner":
        if user[8] != 0: return bot.send_message(uid, "⚠️ You are already in a chat. Use /stop first.")
        bot.send_message(uid, "🔍 Searching for a random partner...")
        # Logic: Find random user who is not in chat
        conn = get_db()
        peer = conn.execute("SELECT user_id FROM users WHERE user_id!=? AND partner_id=0 ORDER BY RANDOM() LIMIT 1", (uid,)).fetchone()
        if peer:
            pid = peer[0]
            conn.execute("UPDATE users SET partner_id=? WHERE user_id=?", (pid, uid))
            conn.execute("UPDATE users SET partner_id=? WHERE user_id=?", (uid, pid))
            conn.commit()
            bot.send_message(uid, "⚡ Connected! Say hi.")
            bot.send_message(pid, "⚡ Connected! Say hi.")
        else: bot.send_message(uid, "⏳ No one available. Try again later.")
        conn.close()

    elif m.text == "💎 Premium Search":
        if user[6] < 1: bot.send_message(uid, "❌ You need 1 ❤️ for Premium Search.")
        else: bot.send_message(uid, "💎 Premium Search active. Choose gender to filter (Experimental).")

    elif m.text == "👤 My Profile":
        bot.send_message(uid, f"👤 Name: {user[2]}\n❤️ Hearts: {user[6]}\n🔗 Your Link: `t.me/{bot.get_me().username}?start={uid}`", parse_mode="Markdown")

    elif m.content_types != 'text' or not m.text.startswith('/'):
        if user[8] != 0:
            try: bot.copy_message(user[8], uid, m.message_id)
            except: bot.send_message(uid, "❌ Partner disconnected.")
        else: bot.send_message(uid, "⚠️ Start a chat first using ⚡ Find a partner.")

@bot.message_handler(commands=['stop'])
def stop_chat(m):
    uid = m.from_user.id
    user = get_user(uid)
    if user and user[8] != 0:
        pid = user[8]
        conn = get_db()
        conn.execute("UPDATE users SET partner_id=0 WHERE user_id IN (?,?)", (uid, pid))
        conn.commit()
        conn.close()
        markup = types.InlineKeyboardMarkup()
        markup.row(types.InlineKeyboardButton("👍", callback_data="rate_up"), types.InlineKeyboardButton("👎", callback_data="rate_down"))
        bot.send_message(uid, "❌ Chat ended. Rate your partner:", reply_markup=markup)
        bot.send_message(pid, "❌ Chat ended. Rate your partner:", reply_markup=markup)
    else: bot.send_message(uid, "❌ You are not in a chat.")

# --- ADMIN INFO ---
@bot.message_handler(commands=['info13'])
def info13(m):
    if m.from_user.id != ADMIN_ID: return
    conn = get_db()
    users = conn.execute("SELECT id, name FROM users LIMIT 30").fetchall()
    res = "📋 User List:\n" + "\n".join([f"{u[0]}. {u[1]}" for u in users])
    bot.send_message(ADMIN_ID, res)

@bot.message_handler(func=lambda m: m.reply_to_message and m.text.isdigit())
def detail(m):
    if m.from_user.id != ADMIN_ID: return
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (int(m.text),)).fetchone()
    if u: bot.send_message(ADMIN_ID, f"🆔 ID: {u[1]}\n👤 Name: {u[2]}\n📍 Loc: {u[3]}\n🎂 Age: {u[5]}\n❤️ Hearts: {u[6]}")

# --- RUN ---
@app.route('/')
def home(): return "Bot Online"
def run_bot(): bot.polling(none_stop=True)
if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
