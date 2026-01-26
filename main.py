import os
import threading
import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- 1. Settings ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
# የሰጠኸኝ ሁለት የ Admin ID ቁጥሮች እዚህ ገብተዋል
ADMINS = [8394878208, 7231324244]

user_data = {} 
users_list = [] 
active_chats = {} 
registration_steps = {} 
waiting_pool = []

# --- 2. Health Check Server ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Live for both Admins!")

def run_health_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- 3. Registration & Core Logic ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        registration_steps[user_id] = "full_name"
        await update.message.reply_text("እንኳን ደህና መጡ! ለመመዝገብ መጀመሪያ ሙሉ ስምዎን ያስገቡ፡")
    else:
        await show_main_menu(update)

async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # የምዝገባ ሂደት
    if user_id in registration_steps:
        step = registration_steps[user_id]
        if step == "full_name":
            user_data[user_id] = {'name': text, 'id': user_id, 'username': update.effective_user.username or "None", 'date': datetime.datetime.now().strftime("%Y-%m-%d")}
            registration_steps[user_id] = "gender"
            await update.message.reply_text("ጾታዎን ያስገቡ (ወንድ/ሴት)፦")
        elif step == "gender":
            user_data[user_id]['gender'] = text
            registration_steps[user_id] = "age"
            await update.message.reply_text("እድሜዎን ያስገቡ፦")
        elif step == "age":
            user_data[user_id]['age'] = text
            registration_steps[user_id] = "location"
            await update.message.reply_text("የሚኖሩበትን ቦታ ያስገቡ፦")
        elif step == "location":
            user_data[user_id]['location'] = text
            del registration_steps[user_id]
            users_list.append(user_id)
            await update.message.reply_text("ምዝገባው ተጠናቅቋል! ✅\n\n🚮for more info @penguiner")
            for admin in ADMINS:
                await context.bot.send_message(admin, f"🆕 አዲስ ተመዝጋቢ፦ {user_data[user_id]['name']}")
            await show_main_menu(update)
        return

    # ቻት ውስጥ ከሆነ
    if user_id in active_chats:
        if text and ("@" in text or "t.me/" in text or "http" in text):
            await update.message.reply_text("⚠️ ዩዘርኔም ወይም ሊንክ መላክ አይቻልም!")
            return
        await update.message.copy(chat_id=active_chats[user_id])

async def show_main_menu(update):
    keyboard = [[InlineKeyboardButton("🎲 Find Partner", callback_data='find')]]
    await update.message.reply_text("ሰው ለመፈለግ ከታች ያለውን ይጫኑ፡", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'find':
        if user_id in active_chats:
            await query.edit_message_text("አሁን በቻት ላይ ነዎት። ለማቆም /stop ይበሉ።")
            return
        
        if user_id not in waiting_pool:
            waiting_pool.append(user_id)
            if len(waiting_pool) >= 2:
                u1 = waiting_pool.pop(0)
                u2 = waiting_pool.pop(0)
                active_chats[u1], active_chats[u2] = u2, u1
                await context.bot.send_message(u1, "🎉 ፓርትነር ተገኝቷል! ማውራት ይችላሉ።")
                await context.bot.send_message(u2, "🎉 ፓርትነር ተገኝቷል! ማውራት ይችላሉ።")
            else:
                await query.edit_message_text("⏳ ሰው እየተፈለገ ነው...")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await context.bot.send_message(user_id, "❌ ቻቱ ቆሟል።")
        await context.bot.send_message(partner_id, "❌ ፓርትነርዎ ቻቱን አቁሟል።")
    else:
        await update.message.reply_text("በቻት ላይ አይደሉም።")

# --- 4. Admin Commands ---

async def admin_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    msg = "📊 የተመዘገቡ ተጠቃሚዎች፦\n\n"
    for i, uid in enumerate(users_list, 1):
        msg += f"{i}. {user_data[uid]['name']} (ID: {uid})\n"
    await update.message.reply_text(msg + "\nለዝርዝር መረጃ ቁጥሩን ሪፕላይ ያድርጉ።")

async def admin_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS or not update.message.reply_to_message: return
    try:
        idx = int(update.message.text) - 1
        target_uid = users_list[idx]
        u = user_data[target_uid]
        await update.message.reply_text(f"👤 መረጃ፦\nስም፡ {u['name']}\nID: {u['id']}\nUsername: @{u['username']}\nጾታ፡ {u['gender']}\nእድሜ፡ {u['age']}\nቦታ፡ {u['location']}\nቀን፡ {u['date']}")
    except:
        await update.message.reply_text("ትክክለኛ ቁጥር ያስገቡ።")

if __name__ == '__main__':
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("information206547", admin_info))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.REPLY, admin_detail))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_all_messages))
    app.run_polling()
