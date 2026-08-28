import os
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# --- CONFIGURATION ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208
# የቻናል ስሞችን ወይም IDዎችን ያግኙ (e.g. "@anonymouslyrobott")
CHANNELS = ["@anonymouslyrobott"]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)


# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect("pro_database.db", check_same_thread=False)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, uid INTEGER UNIQUE, name TEXT, 
                  loc TEXT, gender TEXT, age INTEGER, hearts INTEGER DEFAULT 5, 
                  refs INTEGER DEFAULT 0, partner INTEGER DEFAULT 0, lang TEXT DEFAULT 'am')"""
    )
    conn.commit()
    return conn


db = init_db()
user_steps = {}

# --- TEXTS & LANGUAGES ---
TEXTS = {
    "am": {
        "start": "👋 እንኳን ደህና መጡ! ቦቱን ለመጠቀም መጀመሪያ ይመዝገቡ።\n\nእባክዎ ስምዎን ያስገቡ ✍️:",
        "loc": "📍 መኖሪያ ቦታዎ የት ነው?",
        "age": "🎂 እድሜዎን ያስገቡ (በቁጥር ብቻ 🔢):",
        "gender": "🚻 ጾታዎን ይምረጡ:",
        "join": "⚠️ ቦቱን ለመቀጠል መጀመሪያ ቻናላችንን መቀላቀል አለብዎት:\n\n1️⃣ {ch1}\n\nተቀላቅለው ከሆነ <b>Check ✅</b> የሚለውን ይጫኑ።",
        "main": "🏠 ዋና ማውጫ",
        "search": "🔍 ሸሪክ በመፈለግ ላይ... እባክዎ ይጠብቁ ⏳",
        "found": "⚡ ተገናኝተዋል! አሪፍ ቆይታ ይሁንላችሁ 👋😊\nለመለያየት /stop ይበሉ።",
        "stop": "❌ ቻት ተቋርጧል። ፓርትነርዎን ደረጃ ይስጡ 👇:",
        "heart_err": "❌ Reply ለመጻፍ ቢያንስ 37 ❤️ ያስፈልግዎታል! 💔",
    },
    "en": {
        "start": "👋 Welcome! Please register first to use the bot.\n\nEnter your name ✍️:",
        "loc": "📍 Where do you live?",
        "age": "🎂 Enter your age (numbers only 🔢):",
        "gender": "🚻 Select your gender:",
        "join": "⚠️ You must join our channel first:\n\n1️⃣ {ch1}\n\nIf joined, click <b>Check ✅</b>.",
        "main": "🏠 Main Menu",
        "search": "🔍 Searching for a partner... please wait ⏳",
        "found": "⚡ Connected! Have a great chat 👋😊\nUse /stop to disconnect.",
        "stop": "❌ Chat ended. Rate your partner 👇:",
        "heart_err": "❌ You need at least 37 ❤️ to reply! 💔",
    },
}


# --- HELPERS ---
def is_joined(uid):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, uid).status
            if status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True


def get_u(uid):
    return db.execute("SELECT * FROM users WHERE uid=?", (uid,)).fetchone()


# --- START & REGISTRATION ---
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    u = get_u(uid)

    if not u:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Amharic 🇪🇹", callback_data="l_am"),
            types.InlineKeyboardButton("English 🇺🇸", callback_data="l_en"),
        )
        bot.send_message(
            uid, "🌍 Select Language / ቋንቋ ይምረጡ:", reply_markup=markup
        )
        ref = m.text.split()[1] if len(m.text.split()) > 1 else None
        user_steps[uid] = {"step": "lang", "ref": ref}
    else:
        if not is_joined(uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton(
                    "✅ Check / ቸክ አድርግ", callback_data="check"
                )
            )
            return bot.send_message(
                uid,
                TEXTS[u[9]]["join"].format(ch1=CHANNELS[0]),
                reply_markup=markup,
            )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⚡ Find a partner 🔍", "💎 Premium Search ✨")
        markup.row("👤 My Profile 📝", "⚙️ Settings ⚙️")
        bot.send_message(uid, TEXTS[u[9]]["main"], reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "check")
def check_join(call):
    uid = call.from_user.id
    u = get_u(uid)
    if not u:
        return
    if is_joined(uid):
        bot.delete_message(uid, call.message.message_id)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⚡ Find a partner 🔍", "💎 Premium Search ✨")
        markup.row("👤 My Profile 📝", "⚙️ Settings ⚙️")
        bot.send_message(uid, TEXTS[u[9]]["main"], reply_markup=markup)
    else:
        bot.answer_callback_query(
            call.id,
            "⚠️ ገና አልተቀላቀሉም! እባክዎ መጀመሪያ ቻናሉን ይቀላቀሉ።",
            show_alert=True,
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("l_"))
def set_lang(call):
    uid = call.from_user.id
    lang = call.data.split("_")[1]
    if uid in user_steps:
        user_steps[uid].update({"lang": lang, "step": "name"})
    else:
        user_steps[uid] = {"lang": lang, "step": "name", "ref": None}
    bot.edit_message_text(TEXTS[lang]["start"], uid, call.message.message_id)


@bot.message_handler(
    func=lambda m: m.from_user.id in user_steps
    and user_steps[m.from_user.id].get("step") != "done"
)
def reg_flow(m):
    uid = m.from_user.id
    step = user_steps[uid]["step"]
    lang = user_steps[uid].get("lang", "am")

    if step == "name":
        if len(m.text) < 2:
            return bot.send_message(uid, "❌ ስም ከ 2 ፊደል በላይ መሆን አለበት:")
        user_steps[uid].update({"name": m.text, "step": "loc"})
        bot.send_message(uid, TEXTS[lang]["loc"])

    elif step == "loc":
        user_steps[uid].update({"loc": m.text, "step": "age"})
        bot.send_message(uid, TEXTS[lang]["age"])

    elif step == "age":
        if not m.text.isdigit():
            return bot.send_message(uid, "🔢 ቁጥር ብቻ ያስገቡ:")
        user_steps[uid].update({"age": int(m.text), "step": "gender"})
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        markup.add("Male 👨", "Female 👩")
        bot.send_message(uid, TEXTS[lang]["gender"], reply_markup=markup)

    elif step == "gender":
        d = user_steps[uid]
        db.execute(
            "INSERT INTO users (uid, name, loc, age, gender, lang) VALUES (?,?,?,?,?,?)",
            (uid, d["name"], d["loc"], d["age"], m.text, d["lang"]),
        )

        if d.get("ref"):
            try:
                rid = int(d["ref"])
                db.execute(
                    "UPDATE users SET refs = refs + 1 WHERE uid=?", (rid,)
                )
                refs = db.execute(
                    "SELECT refs FROM users WHERE uid=?", (rid,)
                ).fetchone()
                if refs and refs[0] % 2 == 0:
                    db.execute(
                        "UPDATE users SET hearts = hearts + 1 WHERE uid=?",
                        (rid,),
                    )
                    try:
                        bot.send_message(
                            rid, "❤️ 2 ሰው ስለጋበዙ 1 ልብ ተሰጥቶዎታል! 🎉"
                        )
                    except Exception:
                        pass
            except ValueError:
                pass

        db.commit()

        # ለአድሚን አውቶማቲክ መረጃ መላክ
        bot.send_message(
            ADMIN_ID,
            f"🆕 <b>አዲስ ተመዝጋቢ ይግቢያል:</b>\n\n"
            f"👤 ስም: {d['name']}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            f"📍 ቦታ: {d['loc']}\n"
            f"🎂 እድሜ: {d['age']}\n"
            f"🚻 ጾታ: {m.text}\n"
            f"🌐 ቋንቋ: {d['lang']}",
        )

        del user_steps[uid]
        bot.send_message(uid, "✅ ምዝገባ ተጠናቋል። ለመቀጠል /start ይበሉ።")


# --- CHAT & MEDIA RELAY ---
@bot.message_handler(
    content_types=[
        "text",
        "photo",
        "video",
        "document",
        "voice",
        "animation",
        "sticker",
    ]
)
def relay(m):
    uid = m.from_user.id
    u = get_u(uid)
    if not u:
        return

    # የቻናል ቼክ
    if not is_joined(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "✅ Check / ቸክ አድርግ", callback_data="check"
            )
        )
        return bot.send_message(
            uid,
            TEXTS[u[9]]["join"].format(ch1=CHANNELS[0]),
            reply_markup=markup,
        )

    # 1. ሸሪክ መፈለግ
    if m.text == "⚡ Find a partner 🔍":
        if u[8] != 0:
            return bot.send_message(
                uid, "⚠️ መጀመሪያ ካሉበት ቻት ለመውጣት /stop ይበሉ።"
            )
        bot.send_message(uid, TEXTS[u[9]]["search"])

        p = db.execute(
            "SELECT uid FROM users WHERE uid!=? AND partner=0 ORDER BY RANDOM() LIMIT 1",
            (uid,),
        ).fetchone()
        if p:
            pid = p[0]
            db.execute(
                "UPDATE users SET partner=? WHERE uid=?", (pid, uid)
            )
            db.execute(
                "UPDATE users SET partner=? WHERE uid=?", (uid, pid)
            )
            db.commit()
            bot.send_message(uid, TEXTS[u[9]]["found"])
            bot.send_message(pid, TEXTS[get_u(pid)[9]]["found"])
        else:
            bot.send_message(uid, "⏳ በአሁኑ ሰዓት ሰው አልተገኘም...")

    # 2. ፕሮፋይል ማየት
    elif m.text == "👤 My Profile 📝":
        bot_info = bot.get_me()
        link = f"https://t.me/{bot_info.username}?start={uid}"
        bot.send_message(
            uid,
            f"👤 <b>የእርስዎ መረጃ</b>\n\n❤️ ልብ: {u[6]}\n🔗 መጋበዣ ሊንክ: <code>{link}</code>",
        )

    # 3. መልእክት ማስተላለፍ (Relay)
    elif u[8] != 0:
        if m.reply_to_message and u[6] < 37:
            return bot.send_message(uid, TEXTS[u[9]]["heart_err"])
        try:
            bot.copy_message(u[8], uid, m.message_id)
        except Exception:
            bot.send_message(uid, "❌ መልእክቱ አልደረሰም።")


@bot.message_handler(commands=["stop"])
def stop(m):
    uid = m.from_user.id
    u = get_u(uid)
    if u and u[8] != 0:
        pid = u[8]
        db.execute(
            "UPDATE users SET partner=0 WHERE uid IN (?,?)", (uid, pid)
        )
        db.commit()
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("👍", callback_data="r_good"),
            types.InlineKeyboardButton("👎", callback_data="r_bad"),
        )
        bot.send_message(uid, TEXTS[u[9]]["stop"], reply_markup=markup)
        p_u = get_u(pid)
        if p_u:
            bot.send_message(pid, TEXTS[p_u[9]]["stop"], reply_markup=markup)


# --- ADMIN COMMANDS ---
@bot.message_handler(commands=["ping"])
def ping(m):
    if m.from_user.id != ADMIN_ID:
        return
    msg = m.text.replace("/ping ", "")
    users = db.execute("SELECT uid FROM users").fetchall()
    for u in users:
        try:
            bot.send_message(u[0], f"📢 {msg} 🔔")
        except Exception:
            pass


@bot.message_handler(commands=["info13"])
def info13(m):
    if m.from_user.id != ADMIN_ID:
        return
    res = db.execute("SELECT id, name FROM users LIMIT 50").fetchall()
    txt = "📋 <b>ተጠቃሚዎች:</b>\n" + "\n".join(
        [f"{r[0]}. {r[1]}" for r in res]
    )
    bot.send_message(
        ADMIN_ID, txt + "\n\nዝርዝር መረጃ ለማየት የመታወቂያ ቁጥሩን (ID) Reply ያድርጉ።"
    )


@bot.message_handler(
    func=lambda m: m.from_user.id == ADMIN_ID and m.reply_to_message
)
def admin_detail(m):
    if m.text.isdigit():
        u = db.execute(
            "SELECT * FROM users WHERE id=?", (int(m.text),)
        ).fetchone()
        if u:
            info = f"👤 መረጃ:\n\nID: <code>{u[1]}</code>\nስም: {u[2]}\nቦታ: {u[3]}\nጾታ: {u[4]}\nእድሜ: {u[5]}\n❤️ ልብ: {u[6]}"
            bot.send_message(ADMIN_ID, info)


# --- WEB SERVER & BOT START ---
@app.route("/")
def home():
    return "Bot is Online 🚀"


def run_polling():
    bot.infinity_polling()


if __name__ == "__main__":
    Thread(target=run_polling).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
