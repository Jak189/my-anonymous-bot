import os
import telebot
from flask import Flask
from threading import Thread

# 1. ቦትህን እዚህ ጋር አስተካክል
API_TOKEN = '8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY'
# ያንተን ID ቁጥር እዚህ ጋር አስገባ (ለምሳሌ: 12345678)
ADMIN_ID = 123456789 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# ለ Render ጤንነት ማረጋገጫ (Health Check)
@app.route('/')
def index():
    return "Bot is running and healthy!"

# የ /start ትዕዛዝ ሲላክ
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "እንኳን ደህና መጡ! 👋\n\n"
        "ይህ ማንነትዎ ሳይታወቅ መልዕክት መላኪያ ቦት ነው። "
        "የሚፈልጉትን መልዕክት እዚህ ይጻፉ፤ እኔ ለባለቤቱ አስተላልፋለሁ።"
    )
    bot.reply_to(message, welcome_text)

# መልዕክት ሲላክ ወደ አንተ የሚያስተላልፍበት ክፍል
@bot.message_handler(func=lambda message: True)
def forward_to_admin(message):
    try:
        # ለባለቤቱ (ለአንተ) መረጃውን መላክ
        info = f"📩 **አዲስ መልዕክት ደርሶዎታል**\nከ: {message.from_user.first_name}\nID: `{message.from_user.id}`\n\n**መልዕክት:**\n{message.text}"
        bot.send_message(ADMIN_ID, info, parse_mode="Markdown")
        
        # ለላኪው የተላከ መሆኑን ማረጋገጥ
        bot.reply_to(message, "✅ መልዕክትዎ ለባለቤቱ ደርሷል።")
    except Exception as e:
        print(f"Error: {e}")

# ቦቱ እንዳይቆም በሁለተኛ Thread ማስጀመር
def run_bot():
    bot.polling(none_stop=True)

if __name__ == "__main__":
    # ቦቱን በBackground ማስጀመር
    Thread(target=run_bot).start()
    
    # Flask ሰርቨርን ማስጀመር (Render PORT ይጠቀማል)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
