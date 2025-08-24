import logging
import os
from aiogram import Bot, Dispatcher, executor, types

# Tokenni secrets orqali olish
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bot va dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Foydalanuvchilar ma'lumotlari saqlanadigan oddiy dictionary (demo uchun)
users = {}

# Start buyrug‘i
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id

    # Agar referral link orqali kelsa
    args = message.get_args()
    if args and args.isdigit():
        ref_id = int(args)
        if ref_id != user_id:
            users.setdefault(ref_id, {"balance": 0, "refs": []})
            users[ref_id]["balance"] += 60000
            users[ref_id]["refs"].append(user_id)
            await bot.send_message(ref_id, f"🎉 Yangi do‘st qo‘shildi! Sizga 60 000 UZS qo‘shildi.\n💰 Balansingiz: {users[ref_id]['balance']} UZS")

    # Foydalanuvchini ro‘yxatga olish
    users.setdefault(user_id, {"balance": 0, "refs": []})

    # Asosiy menu
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📊 Balans", "👥 Do‘stingizni Taklif Qiling")
    keyboard.add("📱 Ovoz Berish", "💸 Pul Yechib Olish")

    await message.answer("👋 Salom! Bu yerda siz ovoz berib va do‘stlaringizni taklif qilib pul ishlashingiz mumkin.", reply_markup=keyboard)

# Balans
@dp.message_handler(lambda m: m.text == "📊 Balans")
async def balans_handler(message: types.Message):
    user_id = message.from_user.id
    balance = users.get(user_id, {}).get("balance", 0)
    await message.answer(f"💰 Sizning balansingiz: {balance} UZS")

# Referral link
@dp.message_handler(lambda m: m.text == "👥 Do‘stingizni Taklif Qiling")
async def ref_handler(message: types.Message):
    user_id = message.from_user.id
    link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    await message.answer(f"👥 Do‘stlaringizni taklif qilish uchun link:\n{link}")

# Ovoz berish (telefon raqam so‘rash)
@dp.message_handler(lambda m: m.text == "📱 Ovoz Berish")
async def vote_handler(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📲 Telefon Raqamni Yuborish", request_contact=True)
    keyboard.add(button)
    await message.answer("📲 Ovoz berish uchun telefon raqamingizni yuboring:", reply_markup=keyboard)

# Telefon raqamni qabul qilish
@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    users[user_id]["balance"] += 120000
    await message.answer(f"✅ Raqamingiz qabul qilindi!\n💰 Balansingizga 120 000 UZS qo‘shildi.\nJoriy balans: {users[user_id]['balance']} UZS")

# Pul yechish
@dp.message_handler(lambda m: m.text == "💸 Pul Yechib Olish")
async def withdraw_handler(message: types.Message):
    user_id = message.from_user.id
    balance = users.get(user_id, {}).get("balance", 0)
    if balance >= 300000:
        await message.answer("✅ Pul yechish so‘rovi qabul qilindi. Admin bilan bog‘laning.")
    else:
        await message.answer("❌ Pul yechish uchun kamida 300 000 UZS kerak.")

# Run
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
