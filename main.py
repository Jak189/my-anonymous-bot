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
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, name TEXT, 
                  location TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

user_data = {} # Temporary storage for registration

# --- FLASK FOR RENDER ---
@app.route('/')
def index(): return "Bot is Online"

# --- REGISTRATION LOGIC ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('users.db')
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()

    if user:
        bot.send_message(user_id, f"Welcome back, {user[2]}! Use /menu to explore.")
    else:
        # Handle referral if start has arguments
        args = message.text.split()
        referrer_id = args[1] if len(args) > 1 else None
        
        bot.send_message(user_id, "Welcome! To use this bot, you must register first.\nPlease enter your full name (Minimum 3 characters):")
        user_data[user_id] = {'step': 'name', 'referrer': referrer_id}

@bot.message_handler(func=lambda m: m.from_user.id in user_data)
def register(m):
    uid = m.from_user.id
    step = user_data[uid]['step']

    if step == 'name':
        if len(m.text) < 3:
            bot.reply_to(m, "Name too short! Please enter at least 3 characters:")
        else:
            user_data[uid]['name'] = m.text
            user_data[uid]['step'] = 'location'
            bot.send_message(uid, "Enter your location (City/Address):")

    elif step == 'location':
        user_data[uid]['location'] = m.text
        user_data[uid]['step'] = 'age'
        bot.send_message(uid, "Enter your age (Numbers only):")

    elif step == 'age':
        if not m.text.isdigit():
            bot.reply_to(m, "Please enter a valid number for age:")
        else:
            user_data[uid]['age'] = int(m.text)
            user_data[uid]['step'] = 'gender'
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('Male', 'Female')
            bot.send_message(uid, "Select your gender:", reply_markup=markup)

    elif step == 'gender':
        if m.text not in ['Male', 'Female']:
            bot.reply_to(m, "Please use the buttons to select gender.")
        else:
            gender = m.text
            data = user_data[uid]
            
            # Save to Database
            conn = sqlite3.connect('users.db')
            try:
                conn.execute("INSERT INTO users (user_id, name, location, gender, age) VALUES (?,?,?,?,?)",
                             (uid, data['name'], data['location'], gender, data['age']))
                
                # Handle Referral Credit
                if data['referrer'] and data['referrer'].isdigit():
                    ref_id = int(data['referrer'])
                    conn.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
                    # Check if 2 referrals reached
                    ref_user = conn.execute("SELECT referrals FROM users WHERE user_id = ?", (ref_id,)).fetchone()
                    if ref_user and ref_user[0] % 2 == 0:
                        conn.execute("UPDATE users SET hearts = hearts + 1 WHERE user_id = ?", (ref_id,))
                        bot.send_message(ref_id, "❤️ You earned 1 heart for inviting 2 people!")
                
                conn.commit()
                bot.send_message(uid, "Registration Successful! Use /menu to start.", reply_markup=types.ReplyKeyboardRemove())
                
                # Notify Admin
                admin_msg = f"🆕 New User Registered!\nName: {data['name']}\nAge: {data['age']}\nGender: {gender}"
                bot.send_message(ADMIN_ID, admin_msg)
                
            except Exception as e:
                bot.send_message(uid, "Error in registration. Try /start again.")
            finally:
                conn.close()
                del user_data[uid]

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['info13'])
def admin_info(message):
    if message.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('users.db')
    users = conn.execute("SELECT id, name FROM users LIMIT 50").fetchall()
    conn.close()
    
    res = "📋 Registered Users List:\n"
    for u in users:
        res += f"{u[0]}. {u[1]}\n"
    bot.send_message(ADMIN_ID, res + "\nReply to this message with the ID number to see full details.")

@bot.message_handler(func=lambda m: m.reply_to_message and m.reply_to_message.text.startswith("📋") and m.text.isdigit())
def get_user_detail(m):
    if m.from_user.id != ADMIN_ID: return
    conn = sqlite3.connect('users.db')
    user = conn.execute("SELECT * FROM users WHERE id = ?", (int(m.text),)).fetchone()
    conn.close()
    
    if user:
        detail = (f"👤 Full Info for ID {user[0]}:\n"
                  f"Name: {user[2]}\nLocation: {user[3]}\n"
                  f"Gender: {user[4]}\nAge: {user[5]}\n"
                  f"Hearts: {user[6]}\nReferrals: {user[8]}")
        bot.send_message(ADMIN_ID, detail)
    else:
        bot.reply_to(m, "User ID not found.")

# --- START THREADS ---
def run_bot(): bot.polling(none_stop=True)
if __name__ == "__main__":
    Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
