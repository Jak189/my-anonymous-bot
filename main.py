import os
import sqlite3
import telebot
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
DB_NAME = 'pro_database.db'

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users 
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                      uid INTEGER UNIQUE, 
                      name TEXT, 
                      loc TEXT, 
                      gender TEXT, 
                      age INTEGER, 
                      hearts INTEGER DEFAULT 5, 
                      refs INTEGER DEFAULT 0, 
                      partner INTEGER DEFAULT 0, 
                      lang TEXT DEFAULT 'am')''')
    conn.close()

init_db()
user_steps = {}

# --- TEXTS & LANGUAGES ---
TEXTS = {
    'am': {
        'start': "👋 እንኳን ደህና መጡ! ቦቱን ለመጠቀም መጀመሪያ ይመዝገቡ።\n\nእባክዎ ስምዎን ያስገቡ ✍️:",
        'loc': "📍 መኖሪያ ቦታዎ የት ነው?",
        'age': "🎂 እድሜዎን ያስገቡ (በቁጥር ብቻ 🔢):",
        'gender': "🚻 ጾታዎን ይምረጡ:",
        'join': "⚠️ ቦቱን ለመቀጠል መጀመሪያ ቻናሎቻችንን መቀላቀል አለብዎት:\n\n1️⃣ {ch1}\n2️⃣ {ch2}\n\nተቀላቅለው ከሆነ <b>Check ✅</b> የሚለውን ይጫኑ።",
        'main': "🏠 ዋና ማውጫ",
        'search': "🔍 ሸሪክ በመፈለግ ላይ... እባክዎ ይጠብቁ ⏳",
        'found': "⚡ ተገናኝተዋል! አሪፍ ቆይታ ይሁንላችሁ 👋😊\nለመለያየት /stop ይበሉ።",
        'stop': "❌ ቻት ተቋርጧል። ፓርትነርዎን ደረጃ ይስጡ 👇:",
        'heart_err': "❌ Reply ለመጻፍ ቢያንስ 37 ❤️ ያስፈልግዎታል! 💔"
    },
    'en': {
        'start': "👋 Welcome! Please register first to use the bot.\n\nEnter your name ✍️:",
        'loc': "📍 Where do you live?",
        'age': "🎂 Enter your age (numbers only 🔢):",
        'gender': "🚻 Select your gender:",
        'join': "⚠️ You must join our channels first:\n\n1️⃣ {ch1}\n2️⃣ {ch2}\n\nIf joined, click <b>Check ✅</b>.",
        'main': "🏠 Main Menu",
        'search': "🔍 Searching for a partner... please wait ⏳",
        'found': "⚡ Connected! Have a great chat 👋😊\nUse /stop to disconnect.",
        'stop': "❌ Chat ended. Rate your partner 👇:",
        'heart_err': "❌ You need at least 37 ❤️ to reply! 💔"
    }
}

# --- HELPERS ---
def is_joined(uid):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status in ['left', 'kicked']:
                return False
        except Exception:
            return False
    return True

def get_u(uid):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE uid=?", (uid,))
    user = cursor.fetchone()
    conn.close()
    return user

def show_main_menu(uid, lang):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⚡ Find a partner 🔍", "💎 Premium Search ✨")
    markup.row("👤 My Profile 📝", "⚙️ Settings ⚙️")
    bot.send_message(uid, TEXTS[lang]['main'], reply_markup=markup)

# --- START & REGISTRATION ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    u = get_u(uid)
    
    if not u:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Amharic 🇪🇹", callback_data="l_am"),
            types.InlineKeyboardButton("English 🇺🇸", callback_data="l_en")
        )
        bot.send_message(uid, "🌍 Select Language / ቋንቋ ይምረጡ:", reply_markup=markup)
        ref = m.text.split()[1] if len(m.text.split()) > 1 else None
        user_steps[uid] = {'step': 'lang', 'ref': ref}
    else:
        if not is_joined(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check / ቸክ አድርግ", callback_data="check"))
            return bot.send_message(uid, TEXTS[u['lang']]['join'].format(ch1=CHANNELS[0], ch2=CHANNELS[1]), reply_markup=markup)
        
        show_main_menu(uid, u['lang'])

@bot.callback_query_handler(func=lambda call: call.data == 'check')
def check_join(call):
    uid = call.from_user.id
    u = get_u(uid)
    if not u:
        return bot.answer_callback_query(call.id, "እባክዎ መጀመሪያ ይመዝገቡ /start")
    
    if is_joined(uid):
        bot.delete_message(uid, call.message.message_id)
        show_main_menu(uid, u['lang'])
    else:
        bot.answer_callback_query(call.id, "❌ አሁንም ቻናሎቹን አልተቀላቀሉም!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('l_'))
def set_lang(call):
    uid = call.from_user.id
    lang = call.data.split('_')[1]
    
    if uid not in user_steps:
        user_steps[uid] = {}
        
    user_steps[uid].update({'lang': lang, 'step': 'name'})
    bot.edit_message_text(TEXTS[lang]['start'], uid, call.message.message_id)

@bot.message_handler(func=lambda m: m.from_user.id in user_steps and 'step' in user_steps[m.from_user.id])
def reg_flow(m):
    uid = m.from_user.id
    step = user_steps[uid]['step']
    lang = user_steps[uid].get('lang', 'am')
    
    if step == 'name':
        if len(m.text) < 3:
            return bot.send_message(uid, "❌ ስም ከ 3 ፊደል በላይ መሆን አለበት:")
        user_steps[uid].update({'name': m.text, 'step': 'loc'})
        bot.send_message(uid, TEXTS[lang]['loc'])
        
    elif step == 'loc':
        user_steps[uid].update({'loc': m.text, 'step': 'age'})
        bot.send_message(uid, TEXTS[lang]['age'])
        
    elif step == 'age':
        if not m.text.isdigit():
            return bot.send_message(uid, "🔢 ቁጥር ብቻ ያስገቡ:")
        user_steps[uid].update({'age': int(m.text), 'step': 'gender'})
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add("Male 👨", "Female 👩")
        bot.send_message(uid, TEXTS[lang]['gender'], reply_markup=markup)
        
    elif step == 'gender':
        d = user_steps[uid]
        gender = m.text
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (uid, name, loc, age, gender, lang) VALUES (?,?,?,?,?,?)", 
                       (uid, d['name'], d['loc'], d['age'], gender, d['lang']))
        
        if d.get('ref'):
            try:
                rid = int(d['ref'])
                cursor.execute("UPDATE users SET refs = refs + 1 WHERE uid=?", (rid,))
                cursor.execute("SELECT refs FROM users WHERE uid=?", (rid,))
                ref_res = cursor.fetchone()
                if ref_res and ref_res['refs'] % 2 == 0:
                    cursor.execute("UPDATE users SET hearts = hearts + 1 WHERE uid=?", (rid,))
                    try:
                        bot.send_message(rid, "❤️ 2 ሰው ስለጋበዙ 1 ልብ ተሰጥቶዎታል! 🎉")
                    except Exception:
                        pass
            except ValueError:
                pass
                
        conn.commit()
        conn.close()
        
        try:
            bot.send_message(ADMIN_ID, f"🆕 <b>አዲስ ተመዝጋቢ</b>:\nID: <code>{uid}</code>\nስም: {d['name']}")
        except Exception:
            pass
            
        del user_steps[uid]
        bot.send_message(uid, "✅ ምዝገባ ተጠናቋል።")
        
        u = get_u(uid)
        if not is_joined(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check / ቸክ አድርግ", callback_data="check"))
            bot.send_message(uid, TEXTS[lang]['join'].format(ch1=CHANNELS[0], ch2=CHANNELS[1]), reply_markup=markup)
        else:
            show_main_menu(uid, lang)

# --- CHAT & MEDIA RELAY ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'voice', 'animation', 'sticker'])
def relay(m):
    uid = m.from_user.id
    u = get_u(uid)
    if not u:
        return
    
    # Heart check for reply
    if m.reply_to_message and u['hearts'] < 37:
        return bot.send_message(uid, TEXTS[u['lang']]['heart_err'])

    if m.text == "⚡ Find a partner 🔍":
        if u['partner'] != 0:
            return bot.send_message(uid, "⚠️ መጀመሪያ ካሉበት ቻት ለመውጣት /stop ይበሉ።")
        
        bot.send_message(uid, TEXTS[u['lang']]['search'])
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT uid FROM users WHERE uid!=? AND partner=0 ORDER BY RANDOM() LIMIT 1", (uid,))
        p = cursor.fetchone()
        
        if p:
            pid = p['uid']
            cursor.execute("UPDATE users SET partner=? WHERE uid=?", (pid, uid))
            cursor.execute("UPDATE users SET partner=? WHERE uid=?", (uid, pid))
            conn.commit()
            conn.close()
            
            p_user = get_u(pid)
            bot.send_message(uid, TEXTS[u['lang']]['found'])
            bot.send_message(pid, TEXTS[p_user['lang']]['found'])
        else:
            conn.close()
            bot.send_message(uid, "⏳ በአሁኑ ሰዓት ሰው አልተገኘም...")

    elif m.text == "👤 My Profile 📝":
        bot_username = bot.get_me().username
        link = f"https://t.me/{bot_username}?start={uid}"
        bot.send_message(uid, f"👤 <b>የእርስዎ መረጃ</b>\n\n❤️ ልብ: {u['hearts']}\n🔗 መጋበዣ ሊንክ: <code>{link}</code>")

    # Partner message forwarding
    elif u['partner'] != 0:
        try:
            bot.copy_message(u['partner'], uid, m.message_id)
        except Exception:
            bot.send_message(uid, "❌ መልእክቱ አልደረሰም።")

@bot.message_handler(commands=['stop'])
def stop(m):
    uid = m.from_user.id
    u = get_u(uid)
    if u and u['partner'] != 0:
        pid = u['partner']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET partner=0 WHERE uid IN (?,?)", (uid, pid))
        conn.commit()
        conn.close()
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("👍", callback_data="r_like"),
            types.InlineKeyboardButton("👎", callback_data="r_dislike")
        )
        
        p_user = get_u(pid)
        bot.send_message(uid, TEXTS[u['lang']]['stop'], reply_markup=markup)
        bot.send_message(pid, TEXTS[p_user['lang']]['stop'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('r_'))
def rating_handler(call):
    bot.answer_callback_query(call.id, "ምላሽዎ ተመዝግቧል! አመሰግናለሁ።")
    bot.edit_message_reply_markup(call.from_user.id, call.message.message_id, reply_markup=None)

# --- ADMIN COMMANDS ---
@bot.message_handler(commands=['ping'])
def ping(m):
    if m.from_user.id != ADMIN_ID:
        return
    msg = m.text.replace("/ping ", "")
    if not msg or msg == "/ping":
        return bot.send_message(ADMIN_ID, "⚠️ እባክዎ የሚላከውን መልእክት ያክሉ፦ `/ping አዲስ መረጃ`")
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT uid FROM users")
    users = cursor.fetchall()
    conn.close()
    
    sent_count = 0
    for u in users:
        try:
            bot.send_message(u['uid'], f"📢 {msg} 🔔")
            sent_count += 1
        except Exception:
            pass
    bot.send_message(ADMIN_ID, f"✅ መልእክቱ ለ {sent_count} ተጠቃሚዎች ተልኳል።")

@bot.message_handler(commands=['info13'])
def info13(m):
    if m.from_user.id != ADMIN_ID:
        return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users LIMIT 50")
    res = cursor.fetchall()
    conn.close()
    
    if not res:
        return bot.send_message(ADMIN_ID, "ምንም ተጠቃሚ አልተገኘም።")
        
    txt = "📋 <b>ተጠቃሚዎች:</b>\n" + "\n".join([f"{r['id']}. {r['name']}" for r in res])
    bot.send_message(ADMIN_ID, txt + "\n\nመረጃ ለማየት ቁጥሩን Reply ያድርጉ።")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message)
def admin_detail(m):
    if m.text.isdigit():
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=?", (int(m.text),))
        u = cursor.fetchone()
        conn.close()
        
        if u:
            info = f"👤 መረጃ:\n\nID: <code>{u['uid']}</code>\nስም: {u['name']}\nቦታ: {u['loc']}\nጾታ: {u['gender']}\nእድሜ: {u['age']}\n❤️ ልብ: {u['hearts']}"
            bot.send_message(ADMIN_ID, info)
        else:
            bot.send_message(ADMIN_ID, "❌ በዚህ ID ተጠቃሚ አልተገኘም።")

# --- WEB SERVER ---
@app.route('/')
def home():
    return "Bot is Online 🚀"

def run_polling():
    bot.infinity_polling(skip_pending=callbacks_data_filter if 'callbacks_data_filter' in locals() else True)

if __name__ == "__main__":
    Thread(target=run_polling).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
