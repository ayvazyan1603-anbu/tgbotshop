"""
Запусти ОДИН РАЗ локально для получения file_id и file_unique_id.
После запуска скопируй все переменные в .env на Railway.

  python upload_photos.py
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
    "MAIN":     "photo_main.jpg",
    "STARS":    "photo_stars.jpg",
    "PREMIUM":  "photo_premium.jpg",
    "GIFTS":    "photo_gifts.jpg",
    "PROFILE":  "photo_profile.jpg",
    "REFERRAL": "photo_referral.jpg",
    "SUPPORT":  "photo_support.jpg",
}

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("\n📸 Загружаем фото в Telegram...\n")

    file_ids     = {}
    unique_ids   = {}

    for key, filename in PHOTOS.items():
        if not os.path.exists(filename):
            print(f"⚠️  Файл не найден: {filename} — пропускаем")
            continue
        msg = await bot.send_photo(chat_id=ADMIN_ID, photo=FSInputFile(filename), caption=key)
        file_id        = msg.photo[-1].file_id
        file_unique_id = msg.photo[-1].file_unique_id
        file_ids[f"PHOTO_ID_{key}"]        = file_id
        unique_ids[f"PHOTO_UNIQUE_ID_{key}"] = file_unique_id
        print(f"✅ {key}: file_id получен")

    await bot.session.close()

    print("\n\n📋 Скопируй это в .env на Railway:\n")
    for k, v in file_ids.items():
        print(f"{k}={v}")
    print()
    for k, v in unique_ids.items():
        print(f"{k}={v}")

if __name__ == "__main__":
    asyncio.run(main())