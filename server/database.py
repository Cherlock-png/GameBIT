"""
database.py — Асинхронна SQLite БД
DB_PATH береться зі змінної середовища DATABASE_PATH (для Railway Volume)
або за замовчуванням casino.db поруч з файлом
"""
import aiosqlite
import os
from datetime import datetime, timedelta
from typing import Optional

# Railway Volume монтується в /data — туди і зберігаємо БД
DB_PATH = os.environ.get("DATABASE_PATH",
          os.path.join(os.path.dirname(os.path.abspath(__file__)), "casino.db"))

GAMES = ["blackjack", "slots", "roulette", "durak", "chess", "poker"]

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id         INTEGER PRIMARY KEY,
                username      TEXT,
                first_name    TEXT,
                balance       INTEGER DEFAULT 500,
                last_bonus_time TEXT DEFAULT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id        INTEGER NOT NULL,
                game         TEXT NOT NULL,
                games_played INTEGER DEFAULT 0,
                games_won    INTEGER DEFAULT 0,
                games_lost   INTEGER DEFAULT 0,
                games_draw   INTEGER DEFAULT 0,
                total_bet    INTEGER DEFAULT 0,
                total_won    INTEGER DEFAULT 0,
                FOREIGN KEY (tg_id) REFERENCES users(tg_id),
                UNIQUE(tg_id, game)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id     INTEGER NOT NULL,
                game      TEXT NOT NULL,
                bet       INTEGER NOT NULL,
                result    TEXT NOT NULL,
                payout    INTEGER NOT NULL,
                played_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()

async def get_or_create_user(tg_id: int, username: str = "", first_name: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("INSERT OR IGNORE INTO users (tg_id, username, first_name) VALUES (?,?,?)",
                         (tg_id, username, first_name))
        await db.execute("UPDATE users SET username=?, first_name=? WHERE tg_id=?",
                         (username, first_name, tg_id))
        for game in GAMES:
            await db.execute("INSERT OR IGNORE INTO stats (tg_id, game) VALUES (?,?)", (tg_id, game))
        await db.commit()
        row = await (await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))).fetchone()
        return dict(row)

async def get_user(tg_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,))).fetchone()
        return dict(row) if row else None

async def get_balance(tg_id: int) -> int:
    user = await get_user(tg_id)
    return user["balance"] if user else 0

async def update_balance(tg_id: int, delta: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance = MAX(0, balance + ?) WHERE tg_id=?", (delta, tg_id))
        await db.commit()
        row = await (await db.execute("SELECT balance FROM users WHERE tg_id=?", (tg_id,))).fetchone()
        return row[0] if row else 0

BONUS_AMOUNT   = 500
BONUS_COOLDOWN = timedelta(days=7)

async def claim_bonus(tg_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT balance, last_bonus_time FROM users WHERE tg_id=?", (tg_id,)
        )).fetchone()
        if not row:
            return {"ok": False, "message": "Користувача не знайдено", "balance": 0}
        balance, last_bonus = row["balance"], row["last_bonus_time"]
        if last_bonus:
            last_dt = datetime.fromisoformat(last_bonus)
            next_dt = last_dt + BONUS_COOLDOWN
            if datetime.now() < next_dt:
                remaining = next_dt - datetime.now()
                h = int(remaining.total_seconds() // 3600)
                m = int((remaining.total_seconds() % 3600) // 60)
                return {"ok": False, "message": f"Наступний бонус через {h}г {m}хв",
                        "balance": balance}
        await db.execute(
            "UPDATE users SET balance=balance+?, last_bonus_time=datetime('now') WHERE tg_id=?",
            (BONUS_AMOUNT, tg_id))
        await db.commit()
        return {"ok": True, "message": f"✅ Отримано {BONUS_AMOUNT} монет!",
                "balance": balance + BONUS_AMOUNT, "bonus": BONUS_AMOUNT}

async def get_stats(tg_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute("SELECT * FROM stats WHERE tg_id=?", (tg_id,))).fetchall()
        return {row["game"]: dict(row) for row in rows}

async def update_stats(tg_id: int, game: str, result: str, bet: int, payout: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE stats SET
                games_played = games_played + 1,
                games_won    = games_won  + ?,
                games_lost   = games_lost + ?,
                games_draw   = games_draw + ?,
                total_bet    = total_bet  + ?,
                total_won    = total_won  + ?
            WHERE tg_id=? AND game=?
        """, (1 if result=="win" else 0, 1 if result=="lose" else 0,
              1 if result=="draw" else 0, bet, payout, tg_id, game))
        await db.execute(
            "INSERT INTO game_history (tg_id,game,bet,result,payout) VALUES (?,?,?,?,?)",
            (tg_id, game, bet, result, payout))
        await db.commit()
