import os, asyncio, sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# --- CONFIG ---
TOKEN = "8331406291:AAEHti7O2wVZqV658R-_Kwvu2d65TA_yBAY"
ADMIN_ID = 8394878208
CHANNELS = ["@anonymousely", "@anonymouslyrobott"]
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# --- DB SETUP ---
conn = sqlite3.connect("anonymous_pro.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
    (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, name TEXT, location TEXT, 
     gender TEXT, age INTEGER, hearts INTEGER DEFAULT 5, partner_id INTEGER DEFAULT 0, lang TEXT DEFAULT 'en')''')
conn.commit()

class Registration(StatesGroup):
    name = State()
    location = State()
    age = State()
    gender = State()

# --- HELPERS ---
async def check_join(user_id):
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status == "left": return False
        except: return False
    return True

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    return cursor.fetchone()

# --- START & REGISTRATION ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("👋 Welcome! Please enter your name:")
        await Registration.name.set()
    else:
        if not await check_join(message.from_user.id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Check Joining", callback_data="check"))
            await message.answer(f"⚠️ Please join our channels first:\n1. {CHANNELS[0]}\n2. {CHANNELS[1]}", reply_markup=markup)
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⚡ Find a partner", "💎 Premium Search")
        markup.row("👤 My Profile", "⚙️ Settings")
        await message.answer("🏠 Main Menu", reply_markup=markup)

@dp.message_handler(state=Registration.name)
async def reg_name(message: types.Message, state: FSMContext):
    if len(message.text) < 3:
        await message.answer("❌ Too short! Enter at least 3 letters:")
        return
    await state.update_data(name=message.text)
    await message.answer("📍 Enter your location:")
    await Registration.location.set()

@dp.message_handler(state=Registration.location)
async def reg_loc(message: types.Message, state: FSMContext):
    await state.update_data(location=message.text)
    await message.answer("🎂 Enter your age:")
    await Registration.age.set()

@dp.message_handler(state=Registration.age)
async def reg_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("🔢 Please enter a number:")
        return
    await state.update_data(age=int(message.text))
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Male 👨", "Female 👩")
    await message.answer("🚻 Select your gender:", reply_markup=markup)
    await Registration.gender.set()

@dp.message_handler(state=Registration.gender)
async def reg_gender(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO users (user_id, name, location, age, gender) VALUES (?,?,?,?,?)",
                   (message.from_user.id, data['name'], data['location'], data['age'], message.text))
    conn.commit()
    await state.finish()
    await bot.send_message(ADMIN_ID, f"🆕 New User: {data['name']} | ID: <code>{message.from_user.id}</code>")
    await cmd_start(message)

# --- CHAT LOGIC ---
@dp.message_handler(content_types=['text', 'photo', 'video', 'voice', 'document', 'animation'])
async def handle_chat(message: types.Message):
    user = get_user(message.from_user.id)
    if not user: return

    # Feature 15: Heart limit for replies
    if message.reply_to_message and user[6] < 37:
        await message.answer("❌ You need at least 37 ❤️ to reply to messages!")
        return

    if message.text == "⚡ Find a partner":
        if user[7] != 0:
            await message.answer("⚠️ You are already in a chat! Use /stop first.")
            return
        await message.answer("🔍 Searching for a partner...")
        cursor.execute("SELECT user_id FROM users WHERE user_id != ? AND partner_id = 0 ORDER BY RANDOM() LIMIT 1", (message.from_user.id,))
        partner = cursor.fetchone()
        if partner:
            p_id = partner[0]
            cursor.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (p_id, message.from_user.id))
            cursor.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (message.from_user.id, p_id))
            conn.commit()
            await bot.send_message(p_id, "⚡ Connected! Say hi 👋")
            await message.answer("⚡ Connected! Say hi 👋")
        else:
            await message.answer("⏳ No one found. Try again in a moment.")

    elif message.text == "💎 Premium Search":
        await message.answer("💎 Premium Search costs 1 ❤️. Do you want to continue?")

    elif message.text == "👤 My Profile":
        link = f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"
        await message.answer(f"👤 <b>Your Profile</b>\n\n❤️ Hearts: {user[6]}\n🔗 Share Link: <code>{link}</code>")

    # Relay media/text to partner
    elif user[7] != 0:
        try:
            await bot.copy_message(user[7], message.from_user.id, message.message_id)
        except:
            await message.answer("❌ Partner left the chat.")

# --- STOP CHAT & RATING ---
@dp.message_handler(commands=['stop'])
async def cmd_stop(message: types.Message):
    user = get_user(message.from_user.id)
    if user and user[7] != 0:
        p_id = user[7]
        cursor.execute("UPDATE users SET partner_id = 0 WHERE user_id IN (?,?)", (message.from_user.id, p_id))
        conn.commit()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👍", callback_data="rate_up"), types.InlineKeyboardButton("👎", callback_data="rate_down"))
        await message.answer("❌ Chat ended. Rate your partner:", reply_markup=markup)
        await bot.send_message(p_id, "❌ Chat ended. Rate your partner:", reply_markup=markup)
    else:
        await message.answer("❌ You are not in a chat.")

# --- ADMIN COMMANDS ---
@dp.message_handler(commands=['ping'], user_id=ADMIN_ID)
async def admin_ping(message: types.Message):
    text = message.get_args()
    cursor.execute("SELECT user_id FROM users")
    all_users = cursor.fetchall()
    for u in all_users:
        try: await bot.send_message(u[0], f"📢 <b>Update:</b>\n\n{text}")
        except: pass
    await message.answer("✅ Broadcast sent!")

@dp.message_handler(commands=['info13'], user_id=ADMIN_ID)
async def admin_info(message: types.Message):
    cursor.execute("SELECT id, name FROM users LIMIT 50")
    users = cursor.fetchall()
    res = "📋 <b>User List:</b>\n\n" + "\n".join([f"{u[0]}. {u[1]}" for u in users])
    await message.answer(res)

@dp.message_handler(user_id=ADMIN_ID)
async def admin_detail(message: types.Message):
    if message.reply_to_message and message.text.isdigit():
        cursor.execute("SELECT * FROM users WHERE id=?", (int(message.text),))
        u = cursor.fetchone()
        if u:
            await message.answer(f"🆔 ID: {u[1]}\n👤 Name: {u[2]}\n📍 Loc: {u[3]}\n🚻 Gender: {u[4]}\n🎂 Age: {u[5]}\n❤️ Hearts: {u[6]}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
