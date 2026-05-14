from aiogram import F, Router
from aiogram.types import Message

from app.config import settings
from app.database.session import async_session
from app.keyboards.inline import after_chat_kb
from app.services.matchmaking import enqueue, get_partner, stop_chat, try_match
from app.services.users import get_or_create_user


router = Router()


@router.message(F.text.in_({"🔍 Найти", "⏭ Следующий"}))
async def find_chat(message: Message) -> None:
    if not message.from_user:
        return

    if message.text == "⏭ Следующий":
        await _stop_current_chat(message, silent=True)

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)
        if user.banned:
            await message.answer("🚫 Вы заблокированы.")
            return

        enqueue(user)
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
    partner = stop_chat(uid)

    if not partner:
        if not silent:
            await message.answer("Вы не в чате.")
        return

    if not silent:
        await message.answer("🛑 Чат завершен", reply_markup=after_chat_kb(partner))
    await message.bot.send_message(
        partner,
        "🛑 Собеседник покинул чат",
        reply_markup=after_chat_kb(uid),
    )


@router.message(F.content_type.in_({"text", "photo", "video", "voice", "video_note", "sticker", "document", "audio"}))
async def relay(message: Message) -> None:
    if not message.from_user:
        return

    partner = get_partner(message.from_user.id)
    if not partner:
        return

    if message.video and message.video.file_size and message.video.file_size > settings.MAX_FILE_SIZE:
        await message.answer("❌ Максимальный размер файла 400MB")
        return
    if message.document and message.document.file_size and message.document.file_size > settings.MAX_FILE_SIZE:
        await message.answer("❌ Максимальный размер файла 400MB")
        return
    if message.audio and message.audio.file_size and message.audio.file_size > settings.MAX_FILE_SIZE:
        await message.answer("❌ Максимальный размер файла 400MB")
        return

    await message.copy_to(partner)
