import os
import threading
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. Settings ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMINS = [8394878208, 7231324244]

user_data = {} 
users_list = [] 
active_chats = {} 
registration_steps = {} 
waiting_pool = []

# --- 2. Health Check ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"English Bot is Active!")

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 3. Registration (In English) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        registration_steps[user_id] = "full_name"
        await update.message.reply_text("👋 Welcome to Anonymous Dating Bot!\n\nPlease register first. Enter your full name:")
    else:
        await show_main_menu(update)

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    step = registration_steps[user_id]
    if step == "full_name":
        user_data[user_id] = {'name': text, 'id': user_id, 'username': update.effective_user.username or "None", 'date': datetime.datetime.now().strftime("%Y-%m-%d")}
        registration_steps[user_id] = "gender"
        await update.message.reply_text("Select your gender (Male/Female):")
    elif step == "gender":
        user_data[user_id]['gender'] = text
        registration_steps[user_id] = "age"
        await update.message.reply_text("Enter your age:")
    elif step == "age":
        user_data[user_id]['age'] = text
        registration_steps[user_id] = "location"
        await update.message.reply_text("Enter your city/location:")
    elif step == "location":
        user_data[user_id]['location'] = text
        del registration_steps[user_id]
        users_list.append(user_id)
        await update.message.reply_text("Registration Complete! ✅\n\n🚮 for more info @penguiner")
        for admin in ADMINS:
            await context.bot.send_message(admin, f"🆕 New User Registered: {user_data[user_id]['name']}")
        await show_main_menu(update)

async def show_main_menu(update):
    keyboard = [[InlineKeyboardButton("🎲 Find Partner", callback_data='find')]]
    msg = "Main Menu:"
    if update.message:
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        if update.message.text and ("@" in update.message.text or "t.me/" in update.message.text):
            await update.message.reply_text("⚠️ Sharing usernames/links is not allowed!")
            return
        await update.message.copy(chat_id=partner_id)

# --- 4. Admin Commands (In English) ---

async def admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    msg = "📊 Registered Users:\n\n"
    for i, uid in enumerate(users_list, 1):
        msg += f"{i}. {user_data[uid]['name']} (ID: {uid})\n"
    await update.message.reply_text(msg + "\nReply with the number to see full details.")

async def admin_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS or not update.message.reply_to_message: return
    try:
        idx = int(update.message.text) - 1
        u = user_data[users_list[idx]]
        info = (f"👤 Profile Details:\n\nName: {u['name']}\nID: {u['id']}\nUsername: @{u['username']}\n"
                f"Gender: {u['gender']}\nAge: {u['age']}\nLocation: {u['location']}\nDate: {u['date']}")
        await update.message.reply_text(info)
    except:
        await update.message.reply_text("Invalid number.")

# ... (Rest of the handlers same as before)
