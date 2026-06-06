blackjack.py — Логіка гри Блекджек (повністю на бекенді)
"""
import random
from typing import TypedDict

SUITS = ["♠", "♥", "♦", "♣"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def new_deck() -> list[dict]:
    deck = [{"r": r, "s": s} for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def card_value(card: dict) -> int:
    r = card["r"]
    if r == "A":          return 11
    if r in ("J","Q","K"):return 10
    return int(r)

def hand_total(hand: list[dict]) -> int:
    total = 0
    aces  = 0
    for c in hand:
        total += card_value(c)
        if c["r"] == "A": aces += 1
    while total > 21 and aces:
        total -= 10
        aces  -= 1
    return total

def card_name(card: dict) -> str:
    return f"{card['r']}{card['s']}"

def play_blackjack(bet: int, balance: int) -> dict:
    """
    Повна гра у блекджек на сервері.
    Повертає словник з результатом, картами, балансом.
    """
    if bet <= 0:
        return {"error": "Ставка має бути більше 0"}
    if bet > balance:
        return {"error": "Недостатньо монет"}

    deck = new_deck()

    # Роздача
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop(), deck.pop()]

    player_total = hand_total(player)
    dealer_total = hand_total(dealer)

    log = []  # Покроковий лог для анімації на фронтенді

    log.append({
        "event": "deal",
        "player": list(player),
        "dealer_visible": dealer[0],       # одна відкрита
        "dealer_hidden":  {"r":"?","s":"?"}, # одна закрита
        "player_total": player_total,
    })

    # Натуральний блекджек
    player_bj = player_total == 21
    dealer_bj = dealer_total == 21

    if player_bj or dealer_bj:
        log.append({"event": "reveal_dealer", "dealer": list(dealer), "dealer_total": dealer_total})
        if player_bj and dealer_bj:
            result, payout = "draw", bet
            msg = "🤝 Обидва блекджек — нічия"
        elif player_bj:
            result, payout = "win", int(bet * 2.5)
            msg = "🃏 Блекджек! Ви виграли"
        else:
            result, payout = "lose", 0
            msg = "🃏 Блекджек у дилера"
        return _finish(result, payout, bet, balance, player, dealer, log, msg,
                       player_total, dealer_total)

    # Хід дилера (автоматичний — логіка 17)
    while hand_total(dealer) < 17:
        card = deck.pop()
        dealer.append(card)
        log.append({"event": "dealer_hit", "card": card, "dealer": list(dealer),
                    "dealer_total": hand_total(dealer)})

    dealer_total = hand_total(dealer)
    log.append({"event": "reveal_dealer", "dealer": list(dealer), "dealer_total": dealer_total})

    # Визначення результату
    if player_total > 21:
        result, payout, msg = "lose", 0, "💀 Перебір!"
    elif dealer_total > 21:
        result, payout, msg = "win", bet * 2, "💥 Дилер перебрав!"
    elif player_total > dealer_total:
        result, payout, msg = "win", bet * 2, "✅ Ви виграли!"
    elif dealer_total > player_total:
        result, payout, msg = "lose", 0, "❌ Дилер переміг"
    else:
        result, payout, msg = "draw", bet, "🤝 Нічия"

    return _finish(result, payout, bet, balance, player, dealer, log, msg,
                   player_total, dealer_total)


def _finish(result, payout, bet, balance, player, dealer, log, msg,
            player_total, dealer_total) -> dict:
    balance_delta = payout - bet
    new_balance   = max(0, balance + balance_delta)
    log.append({
        "event": "result",
        "result": result,
        "payout": payout,
        "balance_delta": balance_delta,
        "message": msg
    })
    return {
        "result":        result,       # win / lose / draw
        "payout":        payout,       # скільки повернулось
        "balance_delta": balance_delta,
        "new_balance":   new_balance,
        "player_hand":   [card_name(c) for c in player],
        "dealer_hand":   [card_name(c) for c in dealer],
        "player_total":  player_total,
        "dealer_total":  dealer_total,
        "message":       msg,
        "log":           log,
    }
