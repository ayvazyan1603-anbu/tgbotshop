import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import config
from database.engine import create_tables, seed_gifts
from handlers import setup_routers
from handlers.webhook import create_webhook_app
from middlewares import DbSessionMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    logger.info("Starting bot...")

    await create_tables()
    logger.info("Database tables created/verified.")

    await seed_gifts()
    logger.info("Gifts seeded.")

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(setup_routers())

    tasks = [dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())]

    # Запустить вебхук-сервер только если Fragment API ключ задан
    if config.fragment_api_key:
        webhook_app = create_webhook_app(bot)
        runner = web.AppRunner(webhook_app)
        await runner.setup()
        port = int(os.getenv("PORT", config.webhook_port))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(
            f"Fragment webhook server started on port {config.webhook_port}\n"
            f"  → Endpoint: POST /webhook/fragment\n"
            f"  → Register at: https://v1.fragmentapi.com/partner/dashboard/webhooks"
        )

    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await asyncio.gather(*tasks)
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
