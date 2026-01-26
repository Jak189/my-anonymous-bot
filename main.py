import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"

waiting_users = []
active_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Find a partner", callback_data='find')],
        [InlineKeyboardButton("👤 My Profile", callback_data='profile'),
         InlineKeyboardButton("⚙️ Settings", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👋 Hi! I'm your anonymous chat bot.\n\nClick the button below to start.", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'find':
        if user_id in active_chats:
            await query.edit_message_text("You are already in a chat! Use /stop to leave.")
        elif user_id not in waiting_users:
            waiting_users.append(user_id)
            if len(waiting_users) >= 2:
                u1, u2 = waiting_users.pop(0), waiting_users.pop(0)
                active_chats[u1], active_chats[u2] = u2, u1
                await context.bot.send_message(u1, "🎉 Partner found! Start chatting.")
                await context.bot.send_message(u2, "🎉 Partner found! Start chatting.")
            else:
                await query.edit_message_text("⏳ Searching for a partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(user_id, "❌ Chat stopped.")
        await context.bot.send_message(partner_id, "❌ Your partner left the chat.")
    else:
        await update.message.reply_text("You are not in a chat.")

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        await context.bot.send_message(chat_id=active_chats[user_id], text=update.message.text)

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    app.run_polling()
