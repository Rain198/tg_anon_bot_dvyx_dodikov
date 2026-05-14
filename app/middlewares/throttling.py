from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.services.anti_spam import check_spam, get_flood_count
from app.services.cache import set_online


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            await set_online(event.from_user.id)
            if event.text and event.text.startswith("/"):
                return await handler(event, data)
            if not check_spam(event.from_user.id):
                if get_flood_count(event.from_user.id) in {3, 6}:
                    await event.answer("Слишком быстро. Подождите немного перед следующим сообщением.")
                return None

        return await handler(event, data)
