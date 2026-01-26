import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Find a partner", callback_data='search')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 ሰላም! ይህ የአኖኒመስ ቻት ቦት ነው።\nለመጀመር /search ይጫኑ።", reply_markup=reply_markup)

if __name__ == '__main__':
    # Token በደህንነት ምክንያት ከEnvironment Variable እንዲነበብ ይደረጋል
    TOKEN = os.getenv("BOT_TOKEN") 
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
