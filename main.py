import os
import asyncio
import threading
import aiosqlite
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY")
ADMIN_ID = 8394878208
DB = "users.db"
PORT = int(os.getenv("PORT", 10000))

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ================== DB ==================
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            location TEXT,
            gender TEXT,
            age INTEGER,
            lang TEXT,
            registered INTEGER DEFAULT 0
        )
        """)
        await db.commit()

# ================== TEXT ==================
TEXT = {
    "am": {
        "start": "👋 እንኳን ደህና መጡ\nቋንቋ ይምረጡ",
        "name": "📝 ስምዎን ያስገቡ",
        "location": "📍 መኖሪያ ቦታዎ?",
        "gender": "⚧ ፆታ ይምረጡ",
        "age": "🎂 እድሜዎ?",
        "done": "✅ ተመዝግበዋል!\n/search ብለው ይጀምሩ",
        "search": "🔍 ፓርትነር በመፈለግ ላይ...",
        "stop": "❌ ተለይተዋል\n👍 👎 ሬት ይስጡ"
    }
}

def t(lang, key):
    return TEXT["am"][key]

# ================== HANDLERS ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="lang_am")]
    ]
    await update.message.reply_text(
        TEXT["am"]["start"],
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["lang"] = "am"
    await q.message.reply_text(t("am", "name"))

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "name" not in context.user_data:
        if len(text) < 3:
            return
        context.user_data["name"] = text
        await update.message.reply_text(t("am", "location"))
        return

    if "location" not in context.user_data:
        context.user_data["location"] = text
        kb = [
            [InlineKeyboardButton("👨 Male", callback_data="gender_Male")],
            [InlineKeyboardButton("👩 Female", callback_data="gender_Female")]
        ]
        await update.message.reply_text(
            t("am", "gender"),
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    if "age" not in context.user_data:
        if not text.isdigit():
            return
        context.user_data["age"] = int(text)

        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,1)",
                (
                    update.effective_user.id,
                    context.user_data["name"],
                    context.user_data["location"],
                    context.user_data["gender"],
                    context.user_data["age"],
                    "am"
                )
            )
            await db.commit()

        await update.message.reply_text(t("am", "done"))

        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 New user\n"
            f"Name: {context.user_data['name']}\n"
            f"Gender: {context.user_data['gender']}\n"
            f"Age: {context.user_data['age']}\n"
            f"ID: {update.effective_user.id}"
        )

async def set_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["gender"] = q.data.split("_")[1]
    await q.message.reply_text(t("am", "age"))

# ================== BOT RUN ==================
async def run_bot():
    await init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_lang, pattern="lang_"))
    application.add_handler(CallbackQueryHandler(set_gender, pattern="gender_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register))

    await application.run_polling()

# ================== MAIN ==================
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    asyncio.run(run_bot())
