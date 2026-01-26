import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# ሰርቨር ላይ ምን እየተካሄደ እንደሆነ ለማየት (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ተጠቃሚዎችን ለመያዝ
waiting_users = []  # ሰው የሚጠብቁ
active_chats = {}   # የተገናኙ (User A: User B)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("⚡ Find a partner", callback_data='search')],
        [InlineKeyboardButton("👤 My Profile", callback_data='profile')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Hi, I'm an anonymous chat bot.\nUse the menu or type /search.",
        reply_markup=reply_markup
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ተጠቃሚው ቀድሞውኑ በቻት ውስጥ ከሆነ
    if user_id in active_chats:
        await update.message.reply_text("You are already in a chat! Type /stop to end it.")
        return

    # ተጠቃሚው ቀድሞውኑ ሰርች እያደረገ ከሆነ
    if user_id in waiting_users:
        await update.message.reply_text("Searching for a partner... Please wait.")
        return

    if waiting_users:
        # አጋር ተገኘ!
        partner_id = waiting_users.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        await context.bot.send_message(chat_id=user_id, text="👀 Start chatting!\n/stop - end chat")
        await context.bot.send_message(chat_id=partner_id, text="👀 Start chatting!\n/stop - end chat")
    else:
        # የሚጠብቅ ሰው ከሌለ መጠበቂያ ዝርዝር ውስጥ መግባት
        waiting_users.append(user_id)
        await update.message.reply_text("🔎 Searching for a partner...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        
        await context.bot.send_message(chat_id=user_id, text="🛑 You left the chat.")
        await context.bot.send_message(chat_id=partner_id, text="🛑 Your partner ended the chat.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("Search cancelled.")
    else:
        await update.message.reply_text("You are not in an active chat.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        # መልዕክቱን ለአጋሩ ማስተላለፍ
        if update.message.text:
            await context.bot.send_message(chat_id=partner_id, text=update.message.text)
        elif update.message.photo:
            await context.bot.send_photo(chat_id=partner_id, photo=update.message.photo[-1].file_id)
    else:
        await update.message.reply_text("You are not connected to anyone. Type /search to find a partner.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'search':
        # እዚህ ጋር search ፈንክሽኑን በእጅ መጥራት
        await query.message.reply_text("🔎 Searching...")
        # (ለቀላልነት በቀጥታ ኮዱን እዚህ መቀጠል ይቻላል)
        
if __name__ == '__main__':
    # Render ላይ ስትጭኚ BOT_TOKEN የሚለውን Environment Variable ይጠቀማል
    TOKEN = os.getenv("BOT_TOKEN", "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY")
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Bot is running...")
    app.run_polling()
