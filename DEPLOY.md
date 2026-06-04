# 🚀 Руководство по деплою

## 1. Подготовка VPS

Рекомендуется: Ubuntu 22.04, 1 vCPU, 1 GB RAM.
Провайдеры: Timeweb, Beget, Hetzner.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git -y
```

---

## 2. Загрузить бота на сервер

```bash
# Создать папку
mkdir -p /home/ubuntu/tgbot && cd /home/ubuntu/tgbot

# Загрузить файлы (через scp с локального компьютера):
# scp -r tg_shop_bot/ ubuntu@YOUR_SERVER_IP:/home/ubuntu/tgbot/

# Или через git если есть репозиторий:
# git clone https://github.com/ваш-репо.git .
```

---

## 3. Создать виртуальное окружение

```bash
cd /home/ubuntu/tgbot/tg_shop_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 4. Настроить .env

```bash
cp .env.example .env
nano .env
```

Заполнить обязательно:
```env
BOT_TOKEN=токен_от_BotFather
ADMIN_ID=ваш_telegram_id
SUPPORT_USERNAME=username_поддержки

# PostgreSQL (рекомендуется для продакшна)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/shopdb

# Fragment / iStar
FRAGMENT_API_KEY=ключ_из_istar_dashboard
FRAGMENT_WEBHOOK_SECRET=придумайте_секрет_8_символов

# Lava.ru (СБП)
LAVA_API_KEY=ключ_из_лк_лавы
LAVA_SECRET_KEY=секрет_из_лк_лавы
LAVA_SHOP_ID=id_магазина_лавы

# CryptoBot (TON)
CRYPTOBOT_TOKEN=токен_от_cryptobot

WEBHOOK_PORT=8080
```

---

## 5. Настроить PostgreSQL

```bash
sudo apt install postgresql -y
sudo -u postgres psql

CREATE USER botuser WITH PASSWORD 'StrongPassword123';
CREATE DATABASE shopdb OWNER botuser;
\q
```

---

## 6. Настроить Nginx + SSL (для вебхуков)

Нужен домен. Домен купить на reg.ru (~100 руб/год).
DNS A-запись домена должна указывать на IP вашего сервера.

```bash
# Создать конфиг nginx
sudo nano /etc/nginx/sites-available/tgbot
```

Вставить:
```nginx
server {
    listen 80;
    server_name ВАШ_ДОМЕН.ru;

    location /webhook/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tgbot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Получить SSL сертификат
sudo certbot --nginx -d ВАШ_ДОМЕН.ru
```

После этого вебхуки будут доступны по HTTPS:
- `https://ВАШ_ДОМЕН.ru/webhook/fragment`
- `https://ВАШ_ДОМЕН.ru/webhook/lava`
- `https://ВАШ_ДОМЕН.ru/webhook/cryptobot`

---

## 7. Создать systemd службу

```bash
sudo nano /etc/systemd/system/tgbot.service
```

Вставить:
```ini
[Unit]
Description=Telegram Shop Bot
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/tgbot/tg_shop_bot
ExecStart=/home/ubuntu/tgbot/tg_shop_bot/venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tgbot
sudo systemctl start tgbot

# Проверить логи
sudo journalctl -u tgbot -f
```

---

## 8. Регистрация вебхуков

### Fragment (iStar)
1. Зайти на https://v1.fragmentapi.com/partner/dashboard/webhooks
2. Secret: то же что в `.env` → `FRAGMENT_WEBHOOK_SECRET`
3. URL: `https://ВАШ_ДОМЕН.ru/webhook/fragment`

### Lava.ru
1. Личный кабинет → Магазин → Webhook
2. URL: `https://ВАШ_ДОМЕН.ru/webhook/lava`
3. Secret: то же что `LAVA_SECRET_KEY`

### CryptoBot
1. Написать @CryptoBot → /pay → выбрать приложение → Webhooks
2. URL: `https://ВАШ_ДОМЕН.ru/webhook/cryptobot`

---

## 9. Подтверждение домена в Lava.ru

1. Бизнес кабинет → Проекты → ваш магазин → Подтвердить домен
2. Выбрать способ DNS TXT
3. В панели вашего хостинга добавить TXT запись:
   - Имя: `@`
   - Значение: `lava-verify=XXXXX`
4. Подождать 5-15 минут → нажать "Продолжить"

---

## 10. Получение ключей от CryptoBot

**Основная сеть (продакшн):**
1. Написать @CryptoBot в Telegram
2. `/pay` → Create App → придумать название
3. Скопировать токен → вставить в `CRYPTOBOT_TOKEN`

---

## 11. VPN через HAPP

После деплоя добавлять VPN ключи командой в боте:
```
/addvpn vless://ваш-ключ-из-happ... 30
/addvpn vless://другой-ключ... 90
```

В HAPP панели: Users → выбрать пользователя → Copy link → вставить в /addvpn

---

## 12. Проверка работы

```bash
# Статус бота
sudo systemctl status tgbot

# Логи в реальном времени
sudo journalctl -u tgbot -f

# Проверить вебхук endpoint
curl -X POST https://ВАШ_ДОМЕН.ru/webhook/fragment \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
# Должен вернуть 200 OK
```

---

## Команды администратора (в боте)

| Команда | Описание |
|---|---|
| `/admin` | Статистика и список команд |
| `/addvpn [ключ] [дней]` | Добавить VPN ключ из HAPP |
| `/addgift [название] [цена] [regular\|special]` | Добавить подарок |
| `/editgift [id] [цена]` | Изменить цену подарка |
| `/listgifts` | Список всех подарков |
| `/fbalance` | Баланс TON на Fragment |
| `/broadcast [текст]` | Рассылка всем пользователям |

