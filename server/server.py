"""
server.py — FastAPI сервер з інтерактивним блекджеком і сесіями
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from database import (init_db, get_or_create_user, get_balance,
                      update_balance, claim_bonus, get_stats, get_user, update_stats)
from blackjack import (start_session, hit_session, stand_session,
                       get_session, clear_session)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "webapp", "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# ── Схеми ─────────────────────────────────────────────────────────────────────

class UserReq(BaseModel):
    tg_id:      int
    username:   str = ""
    first_name: str = ""

class BetReq(BaseModel):
    tg_id:      int
    bet:        int = Field(gt=0)
    username:   str = ""
    first_name: str = ""

class ActionReq(BaseModel):
    tg_id: int

# ── Базові ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "Casino server running ✅"}

@app.get("/api/get_user")
async def api_get_user(tg_id: int = Query(...),
                       username: str = Query(""),
                       first_name: str = Query("")):
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

@app.post("/api/bonus")
async def api_bonus(req: UserReq):
    await get_or_create_user(req.tg_id, req.username, req.first_name)
    return await claim_bonus(req.tg_id)

@app.get("/api/stats")
async def api_stats(tg_id: int = Query(...)):
    user = await get_user(tg_id)
    if not user: raise HTTPException(404, "Не знайдено")
    return {"balance": user["balance"], "stats": await get_stats(tg_id)}

# ── Блекджек — сесійний API ───────────────────────────────────────────────────

@app.post("/api/blackjack/start")
async def bj_start(req: BetReq):
    """Почати нову роздачу — списати ставку, роздати карти"""
    user = await get_or_create_user(req.tg_id, req.username, req.first_name)
    if req.bet > user["balance"]:
        raise HTTPException(400, "Недостатньо монет")

    # Списати ставку одразу
    await update_balance(req.tg_id, -req.bet)
    session = start_session(req.tg_id, req.bet, user["balance"] - req.bet)
    session["balance"] = user["balance"] - req.bet

    # Якщо одразу блекджек — закрити сесію і нарахувати виплату
    if session["done"]:
        await _close_session(req.tg_id, session)
        session["balance"] = await get_balance(req.tg_id)

    return session

@app.post("/api/blackjack/hit")
async def bj_hit(req: ActionReq):
    """Взяти ще карту"""
    session = hit_session(req.tg_id)
    if session is None:
        raise HTTPException(400, "Немає активної сесії")
    if session["done"]:
        await _close_session(req.tg_id, session)
        session["balance"] = await get_balance(req.tg_id)
    else:
        session["balance"] = await get_balance(req.tg_id)
    return session

@app.post("/api/blackjack/stand")
async def bj_stand(req: ActionReq):
    """Зупинитись"""
    session = stand_session(req.tg_id)
    if session is None:
        raise HTTPException(400, "Немає активної сесії")
    await _close_session(req.tg_id, session)
    session["balance"] = await get_balance(req.tg_id)
    return session

@app.post("/api/blackjack/double")
async def bj_double(req: ActionReq):
    """Подвоїти ставку — взяти одну карту і стенд"""
    session = get_session(req.tg_id)
    if not session or session["done"]:
        raise HTTPException(400, "Немає активної сесії")
    balance = await get_balance(req.tg_id)
    if balance < session["bet"]:
        raise HTTPException(400, "Недостатньо монет для подвоєння")
    # Списати ще раз ставку
    await update_balance(req.tg_id, -session["bet"])
    # Збільшити ставку в сесії
    from blackjack import _sessions
    _sessions[req.tg_id]["bet"] *= 2
    # Взяти одну карту і стенд
    hit_session(req.tg_id)
    session = stand_session(req.tg_id)
    if session is None:
        session = get_session(req.tg_id)
    await _close_session(req.tg_id, session)
    session["balance"] = await get_balance(req.tg_id)
    return session

@app.get("/api/blackjack/session")
async def bj_session(tg_id: int = Query(...)):
    """Отримати поточну сесію (для відновлення після перезавантаження)"""
    session = get_session(tg_id)
    if not session:
        return {"active": False}
    session["active"]  = True
    session["balance"] = await get_balance(tg_id)
    return session

async def _close_session(tg_id: int, session: dict):
    """Нарахувати виплату і записати статистику"""
    if session["payout"] > 0:
        await update_balance(tg_id, session["payout"])
    await update_stats(
        tg_id=tg_id,
        game="blackjack",
        result=session["result"],
        bet=session["bet"],
        payout=session["payout"]
    )
    clear_session(tg_id)
