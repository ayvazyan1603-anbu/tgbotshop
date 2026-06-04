# 🤖 Digital Marketplace Telegram Bot

Бот для автоматизированной продажи цифровых товаров: Telegram Stars, Premium, подарков и VPN.

## 📁 Структура проекта

```
tg_shop_bot/
├── bot.py                  # Точка входа
├── config.py               # Конфигурация из .env
├── requirements.txt
├── .env.example            # Шаблон переменных окружения
│
├── database/
│   ├── __init__.py
│   ├── engine.py           # SQLAlchemy engine + session factory
│   ├── models.py           # ORM-модели (User, Order, VPNKey, Gift, Transaction)
│   └── repo.py             # Репозиторий — все операции с БД
│
├── handlers/
│   ├── __init__.py         # setup_routers()
│   ├── start.py            # /start, главное меню
│   ├── stars.py            # Покупка Telegram Stars (FSM)
│   ├── premium.py          # Покупка Telegram Premium (FSM)
│   ├── gifts.py            # Покупка подарков (FSM)
│   ├── vpn.py              # Покупка VPN + автовыдача ключа
│   ├── profile.py          # Профиль, пополнение баланса, история
│   ├── referral.py         # Партнёрская программа + вывод
│   └── support_admin.py    # Поддержка + панель администратора
│
├── keyboards/
│   ├── __init__.py
│   └── inline.py           # Все Inline-клавиатуры
│
├── lexicons/
│   ├── __init__.py
│   └── texts.py            # Все тексты бота на русском
│
├── middlewares/
│   ├── __init__.py
│   └── db.py               # Middleware для сессий SQLAlchemy
│
└── services/
    ├── __init__.py
    ├── payment_service.py  # Логика балансов и платежей
    └── vpn_service.py      # Интеграция с Marzban API
```

---

## ⚡ Быстрый старт

### 1. Клонировать и создать окружение

```bash
git clone <your-repo>
cd tg_shop_bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Настройка `.env`

```bash
cp .env.example .env
nano .env
```

Заполните обязательные поля:

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `ADMIN_ID` | Ваш Telegram user ID |
| `SUPPORT_USERNAME` | Username саппорта (без @) |
| `DATABASE_URL` | SQLite или PostgreSQL URL |

### 3. Запуск

```bash
python bot.py
```

---

## 🗄️ База данных

### SQLite (по умолчанию, для разработки)
```env
DATABASE_URL=sqlite+aiosqlite:///./shop.db
```

### PostgreSQL (рекомендуется для продакшна)
```bash
# Установить asyncpg
pip install asyncpg

# В .env:
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/shopdb
```

Таблицы создаются автоматически при запуске.

---

## 🌐 Интеграция с VPN панелью (Marzban)

1. Установите [Marzban](https://github.com/Gozargah/Marzban)
2. Заполните в `.env`:
```env
MARZBAN_URL=https://your-panel.com
MARZBAN_USERNAME=admin
MARZBAN_PASSWORD=your_password
```

Если Marzban недоступен — бот генерирует заглушку ключа (для тестов).

### Альтернатива: предзаготовленные ключи

Добавьте ключи через команду администратора:
```
/addvpn vless://your-key-here... 30
/addvpn vless://another-key... 90
```

---

## 💳 Платёжная система

Сейчас пополнение в **демо-режиме** (мгновенное зачисление без реальной оплаты).

### Подключение Telegram Payments

1. Получите токен провайдера у @BotFather или используйте тестовый: `381764226:TEST:***`
2. Добавьте в `.env`:
```env
PAYMENT_PROVIDER_TOKEN=ваш_токен
```
3. В `handlers/profile.py` раскомментируйте `send_topup_invoice()` вместо демо-зачисления.

---

## 🤝 Партнёрская программа

- Реферальная ссылка: `https://t.me/YourBot?start=ref{user_id}`
- Бонус настраивается: `REFERRAL_PERCENT=10` (10% от каждого пополнения)
- Вывод средств: заявка уходит администратору, тот переводит вручную

---

## ⚙️ Команды администратора

| Команда | Описание |
|---|---|
| `/admin` | Статистика бота |
| `/addvpn [ключ] [дней]` | Добавить VPN ключ в базу |
| `/addgift [название] [цена] [тип]` | Добавить подарок |
| `/broadcast [текст]` | Рассылка всем пользователям |

### Управление заказами
При каждом заказе Stars/Premium/Подарка — администратор получает уведомление с кнопками:
- ✅ **Выполнить** — помечает заказ выполненным, уведомляет покупателя
- ❌ **Отклонить** — возвращает деньги на баланс покупателя

---

## 🔧 Настройка цен

Все цены в `.env` в рублях:

```env
STARS_50_PRICE=100
STARS_100_PRICE=190
STARS_250_PRICE=450
STARS_500_PRICE=850

PREMIUM_3M_PRICE=350
PREMIUM_6M_PRICE=620
PREMIUM_12M_PRICE=1100

VPN_1M_PRICE=150
VPN_3M_PRICE=400
VPN_6M_PRICE=700
```

---

## 📊 Схема БД

```
users          — пользователи, балансы, рефералы
orders         — все заказы с типом, ценой, статусом
vpn_keys       — пул VPN ключей для автовыдачи
gifts          — каталог подарков
transactions   — история движения средств
```

---

## 🚀 Деплой на сервер

```bash
# systemd service
sudo nano /etc/systemd/system/tgshop.service

[Unit]
Description=TG Shop Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/tg_shop_bot
ExecStart=/home/ubuntu/tg_shop_bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

sudo systemctl enable tgshop
sudo systemctl start tgshop
sudo journalctl -u tgshop -f
```
