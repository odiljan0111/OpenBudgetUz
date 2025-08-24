"""
OpenBudget Virtual Referral Bot - O'zbekcha
Har referral: 60 000 UZS (virtual, foydalanuvchi ko'rmaydi)
Minimal yechish: 3 referral = 180 000 UZS
"""

import asyncio
import os
from datetime import datetime, timezone

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.deep_linking import create_start_link
from dotenv import load_dotenv

# -------- CONFIG --------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")
OPEN_BUDGET_URL = os.getenv("OPEN_BUDGET_URL", "")
MIN_REFERRALS = 3         # minimal yechish uchun referral soni
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN .env faylida yo'q!")

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()
DB_PATH = "data.db"

# -------- DATABASE --------
CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    referral_count INTEGER DEFAULT 0,
    referrer_id INTEGER,
    joined_at TEXT
);
"""

CREATE_REFERRALS = """
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    referred_id INTEGER UNIQUE,
    created_at TEXT
);
"""

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_REFERRALS)
        await db.commit()

# -------- DATABASE HELPERS --------
async def upsert_user(user, referrer_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, first_name, username, referrer_id, joined_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                first_name=excluded.first_name,
                username=excluded.username
        """, (user.id, user.first_name or "", user.username or "", referrer_id, datetime.now(timezone.utc).isoformat()))
        await db.commit()

async def ensure_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        result = await db.execute("""
            INSERT OR IGNORE INTO referrals (referrer_id, referred_id, created_at)
            VALUES (?, ?, ?)
        """, (referrer_id, referred_id, datetime.now(timezone.utc).isoformat()))
        # faqat referral sonini oshiramiz, balans foydalanuvchiga ko'rinmaydi
        if result.rowcount > 0:
            await db.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (referrer_id,))
        await db.commit()

async def get_referral_count(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT referral_count FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0

# -------- KEYBOARDS --------
def main_menu(referral_count):
    buttons = [
        [InlineKeyboardButton(text="📊 Ovoz berish", url=OPEN_BUDGET_URL)],
        [InlineKeyboardButton(text="👥 Do'stlarni taklif qilish", callback_data="ref_link")]
    ]
    if referral_count >= MIN_REFERRALS:
        buttons.append([InlineKeyboardButton(text="💰 Pul yechish", callback_data="withdraw")])
    buttons.append([InlineKeyboardButton(text="📄 Biz haqimizda", callback_data="about")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------- HANDLERS --------
@dp.message(CommandStart())
async def on_start(message: Message):
    referrer_id = None
    if message.text and len(message.text.split()) > 1:
        payload = message.text.split(maxsplit=1)[1]
        if payload.startswith("ref_"):
            try:
                referrer_id = int(payload.split("_")[1])
            except:
                pass

    await init_db()
    await upsert_user(message.from_user, referrer_id)
    if referrer_id:
        await ensure_referral(referrer_id, message.from_user.id)

    referral_count = await get_referral_count(message.from_user.id)

    text = (
        f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
        f"📌 Loyiha havolasi: {OPEN_BUDGET_URL}\n"
        f"💰 Minimal pul yechish uchun do'stlaringizni taklif qiling!\n"
        f"💸 1 referral = 60 000 UZS (virtual, foydalanuvchiga ko‘rinmaydi)\n"
        f"💳 Minimal yechish: {MIN_REFERRALS*60000} UZS"
    )
    await message.answer(text, reply_markup=main_menu(referral_count))

@dp.callback_query(F.data == "ref_link")
async def ref_link(cb: CallbackQuery):
    payload = f"ref_{cb.from_user.id}"
    link = await create_start_link(bot, payload)
    await cb.message.answer(f"👥 Do'stlaringizni taklif qilish havolasi:\n{link}")

@dp.callback_query(F.data == "withdraw")
async def withdraw_cb(cb: CallbackQuery):
    await cb.message.answer("💳 Pul yechish arizangiz qabul qilindi! (virtual pul, haqiqiy to‘lov yo‘q)")

@dp.callback_query(F.data == "about")
async def about_cb(cb: CallbackQuery):
    text = (
        "📄 Biz haqimizda:\n\n"
        "🏆 Soxta sertifikatlar va boshqa dokumentlar misollari:\n"
        "1. Sertifikat №12345\n"
        "2. Sertifikat №67890\n"
        "...\n"
        "Ushbu dokumentlar faqat vizual maqsadda."
    )
    await cb.message.answer(text)

# -------- MAIN --------
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
