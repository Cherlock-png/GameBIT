"""
bot.py — Telegram бот на python-telegram-bot 20.7
Запуск: python bot.py
"""
import asyncio
import logging
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database import init_db, get_or_create_user, claim_bonus, get_stats

# ══════════════════════════════════════════════════════════════
BOT_TOKEN  = "8664990924:AAEWWQRd6Yy5_8fxc_PATVE4vQtXJd9hSb0"
WEBAPP_URL = "https://web-production-a8c24.up.railway.app"
# ══════════════════════════════════════════════════════════════

logging.basicConfig(level=logging.INFO)

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 Ігровий Лобі", web_app=WebAppInfo(url=f"{WEBAPP_URL}/"))],
        [InlineKeyboardButton("👤 Мій Профіль", callback_data="profile"),
         InlineKeyboardButton("🎁 500 монет",   callback_data="bonus")],
        [InlineKeyboardButton("❓ Допомога",     callback_data="help")],
    ])

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await get_or_create_user(u.id, u.username or "", u.first_name or "")
    await update.message.reply_text(
        f"♠️ Ласкаво просимо до <b>TG Casino</b>, {u.first_name}!\n\n"
        "💰 На старті тебе чекають <b>500 монет</b>.\n"
        "Щотижня можна отримати безкоштовний бонус!\n\n"
        "Натискай <b>🎰 Ігровий Лобі</b> щоб почати грати 👇",
        parse_mode="HTML", reply_markup=main_menu_kb()
    )

async def cb_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cb = update.callback_query
    await cb.answer()
    u = cb.from_user

    if cb.data == "profile":
        user  = await get_or_create_user(u.id, u.username or "", u.first_name or "")
        stats = await get_stats(u.id)
        bj    = stats.get("blackjack", {})
        played  = bj.get("games_played", 0)
        won     = bj.get("games_won",    0)
        lost    = bj.get("games_lost",   0)
        draw    = bj.get("games_draw",   0)
        winrate = f"{round(won/played*100)}%" if played else "—"
        await cb.message.edit_text(
            f"👤 <b>Профіль</b>\n\n"
            f"🆔 ID: <code>{user['tg_id']}</code>\n"
            f"💰 Баланс: <b>{user['balance']} монет</b>\n\n"
            f"━━━ 🃏 Блекджек ━━━\n"
            f"🎮 Зіграно:   {played}\n"
            f"✅ Виграшів:  {won}\n"
            f"❌ Програшів: {lost}\n"
            f"🤝 Нічиїх:   {draw}\n"
            f"📈 Вінрейт:   {winrate}",
            parse_mode="HTML", reply_markup=main_menu_kb()
        )

    elif cb.data == "bonus":
        result = await claim_bonus(u.id)
        if result["ok"]:
            text = f"🎁 <b>Бонус отримано!</b>\n\n+500 монет!\n💰 Баланс: <b>{result['balance']} монет</b>"
        else:
            text = f"⏳ <b>Бонус ще не доступний</b>\n\n{result['message']}\n💰 Баланс: <b>{result['balance']} монет</b>"
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=main_menu_kb())

    elif cb.data == "help":
        await cb.message.edit_text(
            "❓ <b>Допомога</b>\n\n"
            "🎰 <b>TG Casino</b> — ігрова платформа\n\n"
            "<b>Ігри:</b>\n"
            "• 🃏 Блекджек — доступний!\n"
            "• 🎰 Слоти — скоро\n"
            "• 🎲 Рулетка — скоро\n"
            "• 🃏 Дурак онлайн — скоро\n\n"
            "<b>Монети:</b>\n"
            "• Старт: 500 монет\n"
            "• Щотижня безкоштовний бонус +500\n\n"
            "/start — головне меню",
            parse_mode="HTML", reply_markup=main_menu_kb()
        )

async def main():
    await init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_handler))
    logging.info("Бот запущено...")
    await app.run_polling(skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
