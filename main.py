import os
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# ====== CONFIG ======
TOKEN = os.environ.get("8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN env variable not set")

waiting_users = []          # queue
active_chats = {}           # user_id -> partner_id

# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n"
        "This is an anonymous chat bot.\n\n"
        "Commands:\n"
        "/search - Find a partner\n"
        "/stop - Leave chat"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in active_chats:
        await update.message.reply_text("❗ You are already chatting.")
        return

    if user_id in waiting_users:
        await update.message.reply_text("⏳ Still searching...")
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)

        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        await context.bot.send_message(
            chat_id=user_id,
            text="👀 Partner found! Say hi."
        )
        await context.bot.send_message(
            chat_id=partner_id,
            text="👀 Partner found! Say hi."
        )
    else:
        waiting_users.append(user_id)
        await update.message.reply_text("⏳ Waiting for a partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # If chatting
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)

        await context.bot.send_message(
            chat_id=partner_id,
            text="✋ Partner left the chat."
        )

    # If waiting
    if user_id in waiting_users:
        waiting_users.remove(user_id)

    await update.message.reply_text("👋 You left the chat.")

# ====== MESSAGE FORWARD ======
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if update.message.text:
            await context.bot.send_message(
                chat_id=partner_id,
                text=update.message.text
            )

# ====== MAIN ======
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
