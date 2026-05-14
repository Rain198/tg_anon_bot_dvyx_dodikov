from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message

from app.config import settings
from app.database.session import async_session
from app.keyboards.inline import after_chat_kb
from app.services.matchmaking import enqueue, get_partner, stop_chat, try_match
from app.services.users import get_or_create_user


router = Router()


def _media_file_size(message: Message) -> int | None:
    if message.photo:
        return message.photo[-1].file_size
    if message.video:
        return message.video.file_size
    if message.document:
        return message.document.file_size
    if message.audio:
        return message.audio.file_size
    if message.voice:
        return message.voice.file_size
    if message.video_note:
        return message.video_note.file_size
    return None


@router.message(F.text.in_({"🔍 Найти", "⏭ Следующий"}))
async def find_chat(message: Message) -> None:
    if not message.from_user:
        return

    partner = await get_partner(message.from_user.id)
    if partner and message.text != "⏭ Следующий":
        await message.answer("Вы уже в чате. Используйте «⏭ Следующий» или «🛑 Стоп».")
        return

    if message.text == "⏭ Следующий":
        await _stop_current_chat(message, silent=True)

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        if user.banned:
            await message.answer("🚫 Вы заблокированы.")
            return

        await enqueue(user)
        match = await try_match(session, user.uid)

    if not match:
        await message.answer("🔍 Ищем собеседника...")
        return

    first, second = match
    await message.bot.send_message(first, "✅ Собеседник найден")
    await message.bot.send_message(second, "✅ Собеседник найден")


@router.message(F.text == "🛑 Стоп")
async def stop(message: Message) -> None:
    await _stop_current_chat(message)


async def _stop_current_chat(message: Message, silent: bool = False) -> None:
    if not message.from_user:
        return

    uid = message.from_user.id
    partner = await stop_chat(uid)

    if not partner:
        if not silent:
            await message.answer("Вы не в чате.")
        return

    if not silent:
        await message.answer("🛑 Чат завершен", reply_markup=after_chat_kb(partner))
    try:
        await message.bot.send_message(
            partner,
            "🛑 Собеседник покинул чат",
            reply_markup=after_chat_kb(uid),
        )
    except (TelegramBadRequest, TelegramForbiddenError):
        pass


@router.message(F.content_type.in_({"text", "photo", "video", "voice", "video_note", "sticker", "document", "audio"}))
async def relay(message: Message) -> None:
    if not message.from_user:
        return

    partner = await get_partner(message.from_user.id)
    if not partner:
        return

    file_size = _media_file_size(message)
    if file_size and file_size > settings.MAX_FILE_SIZE:
        await message.answer("❌ Максимальный размер файла 400MB")
        return

    try:
        await message.copy_to(partner)
    except (TelegramBadRequest, TelegramForbiddenError):
        await stop_chat(message.from_user.id)
        await message.answer("Не удалось доставить сообщение. Чат завершен.")
