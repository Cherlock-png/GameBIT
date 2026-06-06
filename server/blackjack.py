"""
blackjack.py — Логіка + сесії блекджеку на бекенді
"""
import random
from typing import Optional

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def new_deck() -> list:
    deck = [{"r": r, "s": s} for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def card_str(c: dict) -> str:
    return f"{c['r']}{c['s']}"

def hand_total(hand: list) -> int:
    total, aces = 0, 0
    for c in hand:
        r = c["r"]
        if r == "A":             total += 11; aces += 1
        elif r in ("J","Q","K"): total += 10
        else:                    total += int(r)
    while total > 21 and aces:
        total -= 10; aces -= 1
    return total

# ── Сесії (в пам'яті, достатньо для одного сервера) ──────────────────────────
_sessions: dict[int, dict] = {}   # tg_id → session

def start_session(tg_id: int, bet: int, balance: int) -> dict:
    deck   = new_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]
    session = {
        "tg_id":   tg_id,
        "bet":     bet,
        "deck":    deck,
        "player":  player,
        "dealer":  dealer,
        "done":    False,
        "result":  None,
        "payout":  0,
        "message": "",
    }
    _sessions[tg_id] = session

    # Перевірка натурального блекджека
    pv = hand_total(player)
    dv = hand_total(dealer)
    if pv == 21 or dv == 21:
        session["done"] = True
        if pv == 21 and dv == 21:
            session["result"], session["payout"], session["message"] = "draw",  bet,          "🤝 Обидва блекджек — нічия"
        elif pv == 21:
            session["result"], session["payout"], session["message"] = "win",   int(bet*2.5), "🃏 Блекджек! x2.5"
        else:
            session["result"], session["payout"], session["message"] = "lose",  0,            "🃏 Блекджек у дилера"

    return _session_view(session)

def hit_session(tg_id: int) -> Optional[dict]:
    s = _sessions.get(tg_id)
    if not s or s["done"]: return None
    s["player"].append(s["deck"].pop())
    pv = hand_total(s["player"])
    if pv > 21:
        s["done"]    = True
        s["result"]  = "lose"
        s["payout"]  = 0
        s["message"] = "💀 Перебір!"
    elif pv == 21:
        return stand_session(tg_id)   # авто-стенд на 21
    return _session_view(s)

def stand_session(tg_id: int) -> Optional[dict]:
    s = _sessions.get(tg_id)
    if not s or s["done"]: return None
    # Дилер добирає до 17
    while hand_total(s["dealer"]) < 17:
        s["dealer"].append(s["deck"].pop())
    pv = hand_total(s["player"])
    dv = hand_total(s["dealer"])
    if   dv > 21:      s["result"], s["payout"], s["message"] = "win",  s["bet"]*2, "💥 Дилер перебрав!"
    elif pv > dv:      s["result"], s["payout"], s["message"] = "win",  s["bet"]*2, "✅ Ви виграли!"
    elif dv > pv:      s["result"], s["payout"], s["message"] = "lose", 0,          "❌ Дилер переміг"
    else:              s["result"], s["payout"], s["message"] = "draw", s["bet"],   "🤝 Нічия"
    s["done"] = True
    return _session_view(s)

def get_session(tg_id: int) -> Optional[dict]:
    s = _sessions.get(tg_id)
    return _session_view(s) if s else None

def clear_session(tg_id: int):
    _sessions.pop(tg_id, None)

def _session_view(s: dict) -> dict:
    done = s["done"]
    return {
        "tg_id":        s["tg_id"],
        "bet":          s["bet"],
        "player_hand":  [card_str(c) for c in s["player"]],
        "dealer_hand":  [card_str(c) for c in s["dealer"]] if done else
                        [card_str(s["dealer"][0]), "??"],
        "player_total": hand_total(s["player"]),
        "dealer_total": hand_total(s["dealer"]) if done else None,
        "done":         done,
        "result":       s["result"],
        "payout":       s["payout"],
        "message":      s["message"],
        "can_double":   not done and len(s["player"]) == 2,
    }
