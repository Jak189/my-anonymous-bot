from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = f"https://t.me/Anonymouslyrobot?start={user_id}"
    await update.message.reply_text(
        f"👋 Welcome!\n\n"
        f"ይህ የአንተ anonymous link ነው:\n{link}\n\n"
        f"ማንም ሰው በዚህ link መልእክት ሊልክልህ ይችላል።"
    )

# receive anonymous message
async def anonymous(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        target_id = int(context.args[0])
        await context.bot.send_message(
            chat_id=target_id,
            text=f"📩 Anonymous message:\n\n{update.message.text}"
        )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, anonymous))

app.run_polling()
