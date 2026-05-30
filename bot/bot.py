"""
bot.py — Telegram бот на aiogram 3.x
Запуск: python bot.py
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, \
                          InlineKeyboardButton, WebAppInfo
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
from database import init_db, get_or_create_user, claim_bonus, get_stats

# ══════════════════════════════════════════════════════════════
BOT_TOKEN   = "ВАШ_ТОКЕН_ВІД_BOTFATHER"
WEBAPP_URL  = "https://ВАШ_СЕРВЕР.up.railway.app"   # URL FastAPI сервера
# ══════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# ─── МЕНЮ ────────────────────────────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Ігровий Лобі",
                              web_app=WebAppInfo(url=f"{WEBAPP_URL}/"))],
        [InlineKeyboardButton(text="👤 Мій Профіль",  callback_data="profile"),
         InlineKeyboardButton(text="🎁 500 монет",    callback_data="bonus")],
        [InlineKeyboardButton(text="❓ Допомога",      callback_data="help")],
    ])

# ─── ХЕНДЛЕРИ ────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = msg.from_user
    await get_or_create_user(user.id, user.username or "", user.first_name or "")
    await msg.answer(
        f"♠️ Ласкаво просимо до <b>TG Casino</b>, {user.first_name}!\n\n"
        "💰 На старті тебе чекають <b>500 монет</b>.\n"
        "Щотижня можна отримати безкоштовний бонус!\n\n"
        "Натискай <b>🎰 Ігровий Лобі</b> щоб почати грати 👇",
        parse_mode="HTML",
        reply_markup=main_menu_kb()
    )

@dp.message(Command("menu"))
async def cmd_menu(msg: Message):
    await msg.answer("Головне меню:", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    user = await get_or_create_user(
        cb.from_user.id, cb.from_user.username or "", cb.from_user.first_name or ""
    )
    stats = await get_stats(cb.from_user.id)
    bj = stats.get("blackjack", {})

    played = bj.get("games_played", 0)
    won    = bj.get("games_won",    0)
    lost   = bj.get("games_lost",   0)
    draw   = bj.get("games_draw",   0)
    winrate = f"{round(won/played*100)}%" if played else "—"

    text = (
        f"👤 <b>Профіль</b>\n\n"
        f"🆔 ID: <code>{user['tg_id']}</code>\n"
        f"👤 Ім'я: {user['first_name']}\n"
        f"💰 Баланс: <b>{user['balance']} монет</b>\n\n"
        f"━━━ 🃏 Блекджек ━━━\n"
        f"🎮 Зіграно:  {played}\n"
        f"✅ Виграшів: {won}\n"
        f"❌ Програшів:{lost}\n"
        f"🤝 Нічиїх:  {draw}\n"
        f"📈 Вінрейт:  {winrate}\n"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())
    await cb.answer()

@dp.callback_query(F.data == "bonus")
async def cb_bonus(cb: CallbackQuery):
    result = await claim_bonus(cb.from_user.id)
    if result["ok"]:
        text = (
            f"🎁 <b>Бонус отримано!</b>\n\n"
            f"+500 монет на рахунок\n"
            f"💰 Баланс: <b>{result['balance']} монет</b>"
        )
    else:
        text = (
            f"⏳ <b>Бонус ще не доступний</b>\n\n"
            f"{result['message']}\n"
            f"💰 Поточний баланс: <b>{result['balance']} монет</b>"
        )
    await cb.answer(result["message"], show_alert=True)
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())

@dp.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery):
    text = (
        "❓ <b>Допомога</b>\n\n"
        "🎰 <b>TG Casino</b> — ігрова платформа\n\n"
        "<b>Ігри:</b>\n"
        "• 🃏 Блекджек — вже доступний!\n"
        "• 🎰 Слоти — скоро\n"
        "• 🎲 Рулетка — скоро\n"
        "• 🃏 Дурак онлайн — скоро\n\n"
        "<b>Монети:</b>\n"
        "• Старт: 500 монет\n"
        "• Щотижня безкоштовний бонус +500\n\n"
        "/start — головне меню\n"
        "/menu — показати меню"
    )
    await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())
    await cb.answer()

# ─── ЗАПУСК ──────────────────────────────────────────────────────────────────

async def main():
    await init_db()
    logging.info("Бот запущено...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
