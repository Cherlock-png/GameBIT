import random
from typing import TypedDict

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

# Словник для збереження поточних ігор гравців. Ключ - tg_id
ACTIVE_GAMES = {}

def new_deck() -> list[dict]:
    deck = [{"r": r, "s": s} for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def card_value(card: dict) -> int:
    r = card["r"]
    if r == "A": return 11
    if r in ("J", "Q", "K"): return 10
    return int(r)

def hand_total(hand: list[dict]) -> int:
    total = sum(card_value(c) for c in hand)
    aces = sum(1 for c in hand if c["r"] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

def card_name(card: dict) -> str:
    return f"{card['r']}{card['s']}"

def format_response(state: dict, result=None, msg="", balance_delta=0, payout=0) -> dict:
    # Ховаємо другу карту дилера, якщо гра триває
    if state["status"] == "playing":
        dealer_hand = [card_name(state["dealer"][0]), "?❓"]
        dealer_tot = card_value(state["dealer"][0])
    else:
        dealer_hand = [card_name(c) for c in state["dealer"]]
        dealer_tot = hand_total(state["dealer"])

    return {
        "status": state["status"], # playing, win, lose, draw
        "result": result,
        "message": msg,
        "balance_delta": balance_delta,
        "payout": payout,
        "player_hand": [card_name(c) for c in state["player"]],
        "dealer_hand": dealer_hand,
        "player_total": hand_total(state["player"]),
        "dealer_total": dealer_tot
    }

def start_game(tg_id: int, bet: int, balance: int) -> dict:
    if bet <= 0: return {"error": "Ставка має бути більше 0"}
    if bet > balance: return {"error": "Недостатньо монет"}

    deck = new_deck()
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]

    state = {
        "bet": bet,
        "deck": deck,
        "player": player,
        "dealer": dealer,
        "status": "playing"
    }
    ACTIVE_GAMES[tg_id] = state

    # Перевірка на натуральний блекджек при роздачі
    p_total = hand_total(player)
    if p_total == 21:
        return stand(tg_id, balance) # Дилер відкриває карти

    return format_response(state)

def hit(tg_id: int, balance: int) -> dict:
    if tg_id not in ACTIVE_GAMES:
        return {"error": "Гру не знайдено"}
    
    state = ACTIVE_GAMES[tg_id]
    state["player"].append(state["deck"].pop())
    
    p_total = hand_total(state["player"])
    
    if p_total > 21:
        # Перебір (Bust)
        state["status"] = "finished"
        response = format_response(state, result="lose", msg="💀 Перебір!", balance_delta=-state["bet"])
        del ACTIVE_GAMES[tg_id]
        return response
        
    return format_response(state)

def stand(tg_id: int, balance: int) -> dict:
    if tg_id not in ACTIVE_GAMES:
        return {"error": "Гру не знайдено"}

    state = ACTIVE_GAMES[tg_id]
    state["status"] = "finished"
    deck = state["deck"]
    dealer = state["dealer"]
    p_total = hand_total(state["player"])

    # Дилер добирає до 17
    while hand_total(dealer) < 17:
        dealer.append(deck.pop())

    d_total = hand_total(dealer)
    bet = state["bet"]

    # Логіка визначення переможця
    if d_total > 21:
        res, payout, msg = "win", bet * 2, "💥 Дилер перебрав!"
    elif p_total > d_total:
        if p_total == 21 and len(state["player"]) == 2:
            res, payout, msg = "win", int(bet * 2.5), "🃏 Блекджек!"
        else:
            res, payout, msg = "win", bet * 2, "✅ Ви виграли!"
    elif d_total > p_total:
        res, payout, msg = "lose", 0, "❌ Дилер переміг"
    else:
        res, payout, msg = "draw", bet, "🤝 Нічия"

    response = format_response(state, result=res, msg=msg, balance_delta=(payout - bet), payout=payout)
    del ACTIVE_GAMES[tg_id]
    return response
