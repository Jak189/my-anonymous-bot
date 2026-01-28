import os
import random
import asyncio
import aiosqlite
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

# ================= CONFIG =================
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
DB_NAME = "users.db"
PORT = int(os.environ.get("PORT", 10000))

# ================= FLASK =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Anonymous Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

def keep_alive():
    Thread(target=run_flask).start()

# ================= DATABASE =================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER
        )
        """)
        await db.commit()

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ================= COMMANDS =================
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Selam!\n\n"
        "ይህ Anonymous Chat Bot ነው 🤖\n\n"
        "➡️ /search ብለህ ሰው ፈልግ\n"
        "⛔ /stop ብለህ chat አቁም"
    )

def search(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    async def _search():
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT partner_id FROM users WHERE user_id=?",
                (user_id,)
            )
            row = await cur.fetchone()
            if row and row[0]:
                return "❗ አሁን በchat ላይ ነህ"

            cur = await db.execute(
                "SELECT user_id FROM users WHERE partner_id IS NULL AND user_id!=?",
                (user_id,)
            )
            free_users = await cur.fetchall()

            if not free_users:
                await db.execute(
                    "INSERT OR REPLACE INTO users (user_id, partner_id) VALUES (?, NULL)",
                    (user_id,)
                )
                await db.commit()
                return "🔍 ሰው በመፈለግ ላይ..."

            partner = random.choice(free_users)[0]

            await db.execute(
                "UPDATE users SET partner_id=? WHERE user_id=?",
                (partner, user_id)
            )
            await db.execute(
                "UPDATE users SET partner_id=? WHERE user_id=?",
                (user_id, partner)
            )
            await db.commit()

            context.bot.send_message(
                chat_id=partner,
                text="✅ ሰው ተገኝቷል! መልእክት ጀምር 🙂"
            )
            return "✅ ሰው ተገኝቷል! መልእክት ጀምር 🙂"

    result = run_async(_search())
    update.message.reply_text(result)

def stop(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    async def _stop():
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT partner_id FROM users WHERE user_id=?",
                (user_id,)
            )
            row = await cur.fetchone()
            if not row or not row[0]:
                return "❗ አሁን chat ላይ አይደለህም"

            partner = row[0]

            await db.execute(
                "UPDATE users SET partner_id=NULL WHERE user_id IN (?,?)",
                (user_id, partner)
            )
            await db.commit()

            context.bot.send_message(
                chat_id=partner,
                text="❌ ባለጋራው chat አቋርጧል"
            )
            return "❌ chat ተቋርጧል"

    result = run_async(_stop())
    update.message.reply_text(result)

def relay(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not update.message.text:
        return

    async def _relay():
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute(
                "SELECT partner_id FROM users WHERE user_id=?",
                (user_id,)
            )
            row = await cur.fetchone()
            if not row or not row[0]:
                return

            partner = row[0]
            context.bot.send_message(
                chat_id=partner,
                text=update.message.text
            )

    run_async(_relay())

# ================= MAIN =================
def main():
    run_async(init_db())
    keep_alive()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("search", search))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, relay))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
