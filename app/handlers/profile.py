from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.session import async_session
from app.keyboards.inline import gender_filter_kb, interests_kb, language_kb
from app.services.users import get_or_create_user


router = Router()


def _interests_label(value: str) -> str:
    return value if value else "не выбраны"


async def _send_profile(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)

    badge = "👑 Premium" if user.premium else "Free"
    text = (
        f"{user.profile_emoji} <b>Профиль</b>\n\n"
        f"Статус: {badge}\n"
        f"Пол: {user.gender or 'не указан'}\n"
        f"Возраст: {user.age or 'не указан'}\n"
        f"Язык: {user.language.upper()}\n"
        f"Интересы: {_interests_label(user.interests)}\n"
        f"Репутация: {user.reputation}\n"
        f"Чатов: {user.chats_count}\n"
        f"Custom status: {user.custom_status or 'нет'}"
    )
    await message.answer(text)


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def profile(message: Message) -> None:
    await _send_profile(message)


@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message) -> None:
    await message.answer("Язык:", reply_markup=language_kb())
    await message.answer("Кого искать:", reply_markup=gender_filter_kb())
    await message.answer("Интересы:", reply_markup=interests_kb())


@router.message(F.text == "👑 Premium")
async def premium(message: Message) -> None:
    await message.answer(
        "👑 <b>Premium</b>\n\n"
        "• Быстрый поиск\n"
        "• Priority queue\n"
        "• Premium badge\n"
        "• Темы и кастомный профиль\n"
        "• Emoji профиля"
    )
