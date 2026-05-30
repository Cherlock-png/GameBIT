# 🎰 TG Casino — Telegram WebApp

Повноцінна ігрова платформа всередині Telegram з економікою на монетах.

## Структура проекту
```
tg-casino/
├── server/
│   ├── server.py       — FastAPI сервер (API + роздача фронтенду)
│   ├── database.py     — Асинхронна SQLite БД
│   └── blackjack.py    — Логіка блекджеку (на бекенді!)
├── bot/
│   └── bot.py          — Telegram бот (aiogram 3.x)
├── webapp/
│   └── static/
│       └── index.html  — Web App (лобі + блекджек)
├── Procfile            — Для Railway
├── requirements.txt
└── README.md
```

## Деплой на Railway (сервер)

### 1. Завантаж на GitHub
Всі файли зі збереженням структури папок.

### 2. Railway → New Project → GitHub repo
Railway підхопить `Procfile` і запустить сервер.

### 3. Отримай URL
Settings → Networking → Generate Domain
→ `https://xxx.up.railway.app`

### 4. Налаштуй bot.py
```python
BOT_TOKEN  = "твій_токен"
WEBAPP_URL = "https://xxx.up.railway.app"
```

### 5. Запусти бота локально
```bash
pip install -r requirements.txt
python bot/bot.py
```

## Локальний запуск (для розробки)

```bash
pip install -r requirements.txt

# Термінал 1 — сервер
cd server
uvicorn server:app --reload --port 8000

# Термінал 2 — бот
cd bot
python bot.py
```

Відкрий браузер: http://localhost:8000

## API Ендпоінти

| Метод | Шлях | Опис |
|-------|------|------|
| GET | `/api/get_user?tg_id=...` | Профіль + статистика |
| POST | `/api/blackjack/play` | Зіграти роздачу |
| POST | `/api/bonus` | Отримати бонус |
| GET | `/api/stats?tg_id=...` | Повна статистика |

## Дорожня карта

- [x] Блекджек (проти казино)
- [ ] Слоти
- [ ] Рулетка
- [ ] Дурак онлайн (PvP + WebSockets)
- [ ] Шахи
- [ ] Покер
