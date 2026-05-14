import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import settings
from app.database.session import init_db
from app.handlers import admin, callbacks, chat, profile, start
from app.middlewares.throttling import ThrottlingMiddleware
from app.services.cache import close_cache


async def main() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL)

    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.message.middleware(ThrottlingMiddleware())

    dp.include_routers(
        start.router,
        profile.router,
        chat.router,
        callbacks.router,
        admin.router,
    )

    try:
        await dp.start_polling(bot)
    finally:
        await close_cache()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
