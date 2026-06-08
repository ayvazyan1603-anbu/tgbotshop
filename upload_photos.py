"""
Запусти этот скрипт ОДИН РАЗ чтобы загрузить фото в Telegram и получить file_id.
После запуска скопируй полученные file_id в .env

Использование:
  pip install aiogram python-dotenv
  python upload_photos.py

Положи фото рядом со скриптом с такими именами:
  photo_main.jpg        — Главное меню
  photo_stars.jpg       — Купить звёзды
  photo_premium.jpg     — Купить премиум
  photo_gifts.jpg       — Удалённые подарки
  photo_profile.jpg     — Профиль
  photo_referral.jpg    — Партнёрская программа
  photo_support.jpg     — Поддержка
"""

import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.types import FSInputFile

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID  = int(os.getenv("ADMIN_ID"))

PHOTOS = {
    "PHOTO_ID_MAIN":     "photo_main.jpg",
    "PHOTO_ID_STARS":    "photo_stars.jpg",
    "PHOTO_ID_PREMIUM":  "photo_premium.jpg",
    "PHOTO_ID_GIFTS":    "photo_gifts.jpg",
    "PHOTO_ID_PROFILE":  "photo_profile.jpg",
    "PHOTO_ID_REFERRAL": "photo_referral.jpg",
    "PHOTO_ID_SUPPORT":  "photo_support.jpg",
}

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("\n📸 Загружаем фото в Telegram...\n")
    results = {}

    for env_key, filename in PHOTOS.items():
        if not os.path.exists(filename):
            print(f"⚠️  Файл не найден: {filename} — пропускаем")
            continue
        msg = await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=FSInputFile(filename),
            caption=f"✅ {env_key}"
        )
        file_id = msg.photo[-1].file_id
        results[env_key] = file_id
        print(f"✅ {env_key}={file_id}")

    await bot.session.close()

    print("\n\n📋 Скопируй это в .env на Railway:\n")
    for k, v in results.items():
        print(f"{k}={v}")

if __name__ == "__main__":
    asyncio.run(main())