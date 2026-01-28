import os
import telebot
from telebot import types
import sqlite3
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208 
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, name TEXT, 
                  location TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()
user_steps = {} 

@app.route('/')
def index(): return "Bot is Online"

# --- HELPER FUNCTIONS ---
def get_user(uid):
    conn = sqlite3.connect('users.db')
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return user

# --- START & REGISTRATION ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    user = get_user(uid)

    if not user:
        # Referral check
        args = message.text.split()
        ref_id = args[1] if len(args) > 1 else None
        
        bot.send_message(uid, "Welcome! Please enter your name to start:")
        user_steps[uid] = {'step': 'name', 'ref': ref_id}
    else:
        main_menu(uid)

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def registration_flow(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']

    if step == 'name':
        if len(m.text) < 3:
            bot.send_message(uid, "Name must be at least 3 characters. Try again:")
        else:
            user_steps[uid]['name'] = m.text
            user_steps[uid]['step'] = 'location'
            bot.send_message(uid, "Enter your location:")
            
    elif step == 'location':
        user_steps[uid]['location'] = m.text
        user_steps[uid]['step'] = 'age'
        bot.send_message(uid, "Enter your age:")
        
    elif step == 'age':
        if not m.text.isdigit():
            bot.send_message(uid, "Please enter age in numbers:")
        else:
            user_steps[uid]['age'] = int(m.text)
            user_steps[uid]['step'] = 'gender'
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('Male', 'Female')
            bot.send_message(uid, "Select your gender:", reply_markup=markup)
            
    elif step == 'gender':
        if m.text not in ['Male', 'Female']:
            bot.send_message(uid, "Please select using the buttons.")
        else:
            data = user_steps[uid]
            conn = sqlite3.connect('users.db')
            conn.execute("INSERT INTO users (user_id, name, location, gender, age) VALUES (?,?,?,?,?)",
                         (uid, data['name'], data['location'], m.text, data['age']))
            
            # Referral logic
            if data['ref'] and data['ref'].isdigit() and int(data['ref']) != uid:
                rid = int(data['ref'])
                conn.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id=?", (rid,))
                ref_data = conn.execute("SELECT referrals FROM users WHERE user_id=?", (rid,)).fetchone()
                if ref_data and ref_data[0] % 2 == 0:
                    conn.execute("UPDATE users SET hearts = hearts + 1 WHERE user_id=?", (rid,))
                    bot.send_message(rid, "❤️ You earned 1 heart for inviting 2 people!")

            conn.commit()
            conn.close()
            bot.send_message(uid, "Registration complete!", reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(ADMIN_ID, f"🆕 New User: {data['name']}\nAge: {data['age']}\nGender: {m.text}\nID: `{uid}`", parse_mode="Markdown")
            del user_steps[uid]
            main_menu(uid)

def main_menu(uid):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Find Partner (1 ❤️)", callback_data="find_partner"))
    markup.add(types.InlineKeyboardButton("My Profile", callback_data="profile"), 
               types.InlineKeyboardButton("Get Hearts", callback_data="get_hearts"))
    bot.send_message(uid, "Main Menu:", reply_markup=markup)

# --- CALLBACK HANDLERS ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    user = get_user(uid)

    if call.data == "profile":
        info = f"👤 Name: {user[2]}\n📍 Loc: {user[3]}\n🚻 Gender: {user[4]}\n🎂 Age: {user[5]}\n❤️ Hearts: {user[6]}"
        bot.answer_callback_query(call.id)
        bot.send_message(uid, info)

    elif call.data == "get_hearts":
        bot.send_message(uid, f"Invite 2 friends to get 1 ❤️\nYour link: `t.me/{bot.get_me().username}?start={uid}`", parse_mode="Markdown")

    elif call.data == "find_partner":
        if user[6] < 1:
            bot.send_message(uid, "You need at least 1 ❤️. Buy stars or invite friends.")
            # እዚህ ጋር ለ Star ክፍያ እንዲልኩ መጠየቅ ይቻላል
        else:
            # የልብ ቅነሳ
            conn = sqlite3.connect('users.db')
            conn.execute("UPDATE users SET hearts = hearts - 1 WHERE user_id=?", (uid,))
            conn.commit()
            conn.close()
            bot.send_message(uid, "Looking for a partner... (Feature coming soon)")

# --- CHAT SYSTEM ---
@bot.message_handler(func=lambda m: True)
def handle_chat(m):
    # Admin reply logic
    if m.from_user.id == ADMIN_ID and m.reply_to_message:
        try:
            target_id = m.reply_to_message.text.split("ID: `")[1].split("`")[0]
            bot.send_message(target_id, f"Message from Admin:\n\n{m.text}")
            bot.reply_to(m, "Sent!")
        except:
            bot.reply_to(m, "Error: User ID not found.")
        return

    # Regular chat to Admin
    user = get_user(m.from_user.id)
    if user:
        bot.send_message(ADMIN_ID, f"📩 From: {user[2]}\nID: `{m.from_user.id}`\n\n{m.text}", parse_mode="Markdown")
        bot.reply_to(m, "Message sent to Admin.")

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['info13'])
def admin_list(message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('users.db')
    users = conn.execute("SELECT id, name FROM users LIMIT 30").fetchall()
    conn.close()
    res = "📋 User List:\n"
    for u in users: res += f"{u[0]}. {u[1]}\n"
    bot.send_message(ADMIN_ID, res + "\nReply with the number to see details.")

@bot.message_handler(func=lambda m: m.reply_to_message and "📋 User List" in m.reply_to_message.text and m.text.isdigit())
def admin_detail(m):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('users.db')
    user = conn.execute("SELECT * FROM users WHERE id=?", (int(m.text),)).fetchone()
    conn.close()
    if user:
        detail = f"👤 User {user[0]}:\nName: {user[2]}\nLoc: {user[3]}\nGender: {user[4]}\nAge: {user[5]}\nHearts: {user[6]}\nRefs: {user[7]}"
        bot.send_message(ADMIN_ID, detail)

def run_bot(): bot.polling(none_stop=True)
if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
