"""
database.py — Асинхронна база даних SQLite
"""
import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = "casino.db"

GAMES = ["blackjack", "slots", "roulette", "durak", "chess", "poker"]

# ─── ІНІЦІАЛІЗАЦІЯ ────────────────────────────────────────────────────────────

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Користувачі
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
        # Статистика по іграх
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id       INTEGER NOT NULL,
                game        TEXT NOT NULL,
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
        # Історія ігор
        await db.execute("""
            CREATE TABLE IF NOT EXISTS game_history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id     INTEGER NOT NULL,
                game      TEXT NOT NULL,
                bet       INTEGER NOT NULL,
                result    TEXT NOT NULL,
                payout    INTEGER NOT NULL,
                details   TEXT,
                played_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.commit()

# ─── КОРИСТУВАЧІ ─────────────────────────────────────────────────────────────

async def get_or_create_user(tg_id: int, username: str = "", first_name: str = "") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Створити якщо не існує
        await db.execute("""
            INSERT OR IGNORE INTO users (tg_id, username, first_name)
            VALUES (?, ?, ?)
        """, (tg_id, username, first_name))
        # Оновити ім'я якщо змінилось
        await db.execute("""
            UPDATE users SET username=?, first_name=?
            WHERE tg_id=?
        """, (username, first_name, tg_id))
        # Створити статистику для всіх ігор
        for game in GAMES:
            await db.execute("""
                INSERT OR IGNORE INTO stats (tg_id, game)
                VALUES (?, ?)
            """, (tg_id, game))
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM users WHERE tg_id=?", (tg_id,)
        )).fetchone()
        return dict(row)

async def get_user(tg_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT * FROM users WHERE tg_id=?", (tg_id,)
        )).fetchone()
        return dict(row) if row else None

async def get_balance(tg_id: int) -> int:
    user = await get_user(tg_id)
    return user["balance"] if user else 0

async def update_balance(tg_id: int, delta: int) -> int:
    """Змінює баланс на delta (може бути від'ємним). Повертає новий баланс."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET balance = MAX(0, balance + ?) WHERE tg_id=?
        """, (delta, tg_id))
        await db.commit()
        row = await (await db.execute(
            "SELECT balance FROM users WHERE tg_id=?", (tg_id,)
        )).fetchone()
        return row[0] if row else 0

# ─── БОНУС ───────────────────────────────────────────────────────────────────

BONUS_AMOUNT    = 500
BONUS_COOLDOWN  = timedelta(days=7)   # щотижнево
BONUS_THRESHOLD = 100                 # видати бонус якщо баланс < 100 (опційно)

async def claim_bonus(tg_id: int) -> dict:
    """
    Нараховує 500 монет якщо минув тиждень з останнього бонусу.
    Повертає {"ok": True/False, "message": str, "balance": int}
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute(
            "SELECT balance, last_bonus_time FROM users WHERE tg_id=?", (tg_id,)
        )).fetchone()
        if not row:
            return {"ok": False, "message": "Користувача не знайдено", "balance": 0}

        balance = row["balance"]
        last_bonus = row["last_bonus_time"]

        if last_bonus:
            last_dt = datetime.fromisoformat(last_bonus)
            next_dt = last_dt + BONUS_COOLDOWN
            if datetime.now() < next_dt:
                remaining = next_dt - datetime.now()
                hours = int(remaining.total_seconds() // 3600)
                mins  = int((remaining.total_seconds() % 3600) // 60)
                return {
                    "ok": False,
                    "message": f"Наступний бонус через {hours}г {mins}хв",
                    "balance": balance,
                    "next_bonus": next_dt.isoformat()
                }

        await db.execute("""
            UPDATE users
            SET balance = balance + ?, last_bonus_time = datetime('now')
            WHERE tg_id=?
        """, (BONUS_AMOUNT, tg_id))
        await db.commit()
        new_balance = balance + BONUS_AMOUNT
        return {
            "ok": True,
            "message": f"✅ Отримано {BONUS_AMOUNT} монет!",
            "balance": new_balance,
            "bonus": BONUS_AMOUNT
        }

# ─── СТАТИСТИКА ──────────────────────────────────────────────────────────────

async def get_stats(tg_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(
            "SELECT * FROM stats WHERE tg_id=?", (tg_id,)
        )).fetchall()
        return {row["game"]: dict(row) for row in rows}

async def update_stats(tg_id: int, game: str, result: str, bet: int, payout: int):
    """result: 'win' | 'lose' | 'draw'"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"""
            UPDATE stats SET
                games_played = games_played + 1,
                games_won    = games_won  + ?,
                games_lost   = games_lost + ?,
                games_draw   = games_draw + ?,
                total_bet    = total_bet  + ?,
                total_won    = total_won  + ?
            WHERE tg_id=? AND game=?
        """, (
            1 if result == "win"  else 0,
            1 if result == "lose" else 0,
            1 if result == "draw" else 0,
            bet, payout, tg_id, game
        ))
        await db.execute("""
            INSERT INTO game_history (tg_id, game, bet, result, payout)
            VALUES (?, ?, ?, ?, ?)
        """, (tg_id, game, bet, result, payout))
        await db.commit()
