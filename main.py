import os, sqlite3, telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208 
CHANNEL_URL = "https://t.me/anonymousely"
CHANNEL_ID = "@anonymousely" # ቻናሉ ላይ ቦቱን አድሚን አድርገው
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE ---
def get_db():
    conn = sqlite3.connect('anonymous.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, name TEXT, 
                  location TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()
user_steps = {}

# --- MIDDLEWARE: CHECK JOIN ---
def is_joined(uid):
    try:
        status = bot.get_chat_member(CHANNEL_ID, uid).status
        return status in ['member', 'administrator', 'creator']
    except:
        return True # ቻናሉ የግል ከሆነ ወይም ቦቱ አድሚን ካልሆነ

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
    if not is_joined(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Join Channel", url=CHANNEL_URL))
        return bot.send_message(uid, f"You must join our channel to use this bot:\n{CHANNEL_URL}", reply_markup=markup)

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    if not user:
        bot.send_message(uid, "Welcome! Enter your name:")
        user_steps[uid] = {'step': 'name'}
    else:
        bot.send_message(uid, "Main Menu", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def register(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']

    if step == 'name':
        if len(m.text) < 3: bot.send_message(uid, "Enter at least 3 letters:")
        else:
            user_steps[uid]['name'] = m.text
            user_steps[uid]['step'] = 'loc'; bot.send_message(uid, "Your Location:")
    elif step == 'loc':
        user_steps[uid]['loc'] = m.text
        user_steps[uid]['step'] = 'age'; bot.send_message(uid, "Your Age:")
    elif step == 'age' and m.text.isdigit():
        user_steps[uid]['age'] = int(m.text)
        user_steps[uid]['step'] = 'gender'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Male", "Female")
        bot.send_message(uid, "Gender:", reply_markup=markup)
    elif step == 'gender':
        conn = get_db()
        conn.execute("INSERT INTO users (user_id, name, location, gender, age) VALUES (?,?,?,?,?)",
                     (uid, user_steps[uid]['name'], user_steps[uid]['loc'], m.text, user_steps[uid]['age']))
        conn.commit()
        conn.close()
        bot.send_message(uid, "Registered!", reply_markup=main_menu())
        # አድሚን ጋር የሚላከው የተመዝጋቢው ስም እና ID ብቻ ነው
        bot.send_message(ADMIN_ID, f"🆕 New User: {user_steps[uid]['name']} | ID: `{uid}`", parse_mode="Markdown")
        del user_steps[uid]

# --- BROADCAST COMMAND ---
@bot.message_handler(commands=['ping'])
def ping_all(message):
    if message.from_user.id != ADMIN_ID: return
    text = message.text.replace("/ping ", "")
    conn = get_db()
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    for u in users:
        try: bot.send_message(u[0], text)
        except: pass
    bot.reply_to(message, "Sent to all users!")

# --- FEATURES ---
@bot.message_handler(func=lambda m: True)
def handle_features(m):
    uid = m.from_user.id
    if m.text == "⚡ Find a partner":
        bot.send_message(uid, "Searching for a random partner...")
    elif m.text == "💎 Premium Search":
        conn = get_db()
        user = conn.execute("SELECT hearts FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        if user[0] < 1:
            bot.send_message(uid, "This feature costs 1 ❤️. Invite friends or buy Stars.")
        else:
            bot.send_message(uid, "Select gender to search:")
    elif m.text == "👤 My Profile":
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        bot.send_message(uid, f"Name: {u[2]}\nHearts: {u[6]}\nLink: `t.me/{bot.get_me().username}?start={uid}`", parse_mode="Markdown")

# --- ADMIN INFO ---
@bot.message_handler(commands=['info13'])
def info13(m):
    if m.from_user.id != ADMIN_ID: return
    conn = get_db()
    users = conn.execute("SELECT id, name FROM users").fetchall()
    conn.close()
    res = "📋 Users:\n" + "\n".join([f"{u[0]}. {u[1]}" for u in users])
    bot.send_message(ADMIN_ID, res)

@bot.message_handler(func=lambda m: m.reply_to_message and m.text.isdigit())
def info_detail(m):
    if m.from_user.id != ADMIN_ID: return
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (int(m.text),)).fetchone()
    conn.close()
    if u: bot.send_message(ADMIN_ID, f"Full Info:\nName: {u[2]}\nLoc: {u[3]}\nAge: {u[5]}\nID: {u[1]}")

# --- RUN ---
@app.route('/')
def h(): return "Bot Active"
def r(): bot.polling(none_stop=True)
if __name__ == "__main__":
    Thread(target=r).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
