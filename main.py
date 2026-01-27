import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.environ.get("8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN not set")

waiting = []
chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Anonymous Chat Bot\n"
        "/search - find partner\n"
        "/stop - leave chat"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in chats:
        return await update.message.reply_text("❗ Already chatting")

    if waiting:
        partner = waiting.pop(0)
        chats[uid] = partner
        chats[partner] = uid
        await context.bot.send_message(uid, "👀 Partner found!")
        await context.bot.send_message(partner, "👀 Partner found!")
    else:
        waiting.append(uid)
        await update.message.reply_text("⏳ Waiting...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in chats:
        partner = chats.pop(uid)
        chats.pop(partner, None)
        await context.bot.send_message(partner, "✋ Partner left")
    if uid in waiting:
        waiting.remove(uid)
    await update.message.reply_text("👋 Left chat")

async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in chats and update.message.text:
        await context.bot.send_message(chats[uid], update.message.text)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, forward))
    app.run_polling()

if __name__ == "__main__":
    main()
