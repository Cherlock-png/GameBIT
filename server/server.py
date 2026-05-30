"""
server.py — FastAPI API сервер для Telegram Casino WebApp
Запуск: uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import init_db, get_or_create_user, get_balance, update_balance, \
                     claim_bonus, get_stats, update_stats, get_user
from blackjack import play_blackjack

# ─── LIFESPAN ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# Роздаємо фронтенд
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "webapp", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# ─── СХЕМИ ───────────────────────────────────────────────────────────────────

class BlackjackRequest(BaseModel):
    tg_id:      int
    bet:        int = Field(gt=0, description="Ставка > 0")
    username:   str = ""
    first_name: str = ""

class BonusRequest(BaseModel):
    tg_id:      int
    username:   str = ""
    first_name: str = ""

# ─── ЕНДПОІНТИ ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "Casino server running ✅"}

@app.get("/api/get_user")
async def api_get_user(
    tg_id:      int = Query(...),
    username:   str = Query(""),
    first_name: str = Query("")
):
    """Отримати або створити користувача"""
    user  = await get_or_create_user(tg_id, username, first_name)
    stats = await get_stats(tg_id)
    bj    = stats.get("blackjack", {})
    return {
        "tg_id":      user["tg_id"],
        "username":   user["username"],
        "first_name": user["first_name"],
        "balance":    user["balance"],
        "stats": {
            "blackjack": {
                "played": bj.get("games_played", 0),
                "won":    bj.get("games_won",    0),
                "lost":   bj.get("games_lost",   0),
                "draw":   bj.get("games_draw",   0),
            }
        }
    }

@app.post("/api/blackjack/play")
async def api_blackjack_play(req: BlackjackRequest):
    """Зіграти одну роздачу блекджеку"""
    user = await get_or_create_user(req.tg_id, req.username, req.first_name)
    balance = user["balance"]

    game = play_blackjack(req.bet, balance)

    if "error" in game:
        raise HTTPException(status_code=400, detail=game["error"])

    # Оновити баланс та статистику
    await update_balance(req.tg_id, game["balance_delta"])
    await update_stats(
        tg_id=req.tg_id,
        game="blackjack",
        result=game["result"],
        bet=req.bet,
        payout=game["payout"]
    )

    game["balance"] = game["new_balance"]
    return game

@app.post("/api/bonus")
async def api_claim_bonus(req: BonusRequest):
    """Отримати щотижневий бонус"""
    await get_or_create_user(req.tg_id, req.username, req.first_name)
    return await claim_bonus(req.tg_id)

@app.get("/api/stats")
async def api_get_stats(tg_id: int = Query(...)):
    """Повна статистика гравця"""
    user = await get_user(tg_id)
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    stats = await get_stats(tg_id)
    return {"balance": user["balance"], "stats": stats}
