from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings
from app.database.session import async_session
from app.keyboards.inline import (
    INTERESTS,
    PROFILE_THEMES,
    gender_filter_kb,
    interests_kb,
    language_kb,
    profile_gender_kb,
    profile_settings_kb,
)
from app.services.users import get_or_create_user, update_user


router = Router()
pending_profile_inputs: dict[int, str] = {}

GENDER_LABELS = {
    "": "не указан",
    "male": "парень",
    "female": "девушка",
    "any": "любой",
}


def _interests_label(value: str) -> str:
    if not value:
        return "не выбраны"
    return ", ".join(INTERESTS.get(item, item) for item in value.split(",") if item)


def _profile_text(user) -> str:
    badge = "👑 Premium" if user.premium else "Free"
    theme_label = PROFILE_THEMES.get(user.theme, user.theme)
    filter_label = GENDER_LABELS.get(user.preferred_gender, "любой")
    return (
        f"{user.profile_emoji} <b>Профиль</b>\n\n"
        f"Статус: {badge}\n"
        f"Пол: {GENDER_LABELS.get(user.gender, 'не указан')}\n"
        f"Возраст: {user.age or 'не указан'}\n"
        f"Язык поиска: {user.language.upper()}\n"
        f"Фильтр пола: {filter_label}\n"
        f"Интересы: {_interests_label(user.interests)}\n"
        f"Репутация: {user.reputation}\n"
        f"Чатов: {user.chats_count}\n"
        f"Theme: {theme_label}\n"
        f"Custom status: {user.custom_status or 'нет'}"
    )


async def _send_profile(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)

    await message.answer(_profile_text(user))


@router.message(Command("profile"))
@router.message(F.text == "👤 Профиль")
async def profile(message: Message) -> None:
    await _send_profile(message)


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def settings_menu(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)

    selected_interests = {item for item in user.interests.split(",") if item}
    await message.answer("⚙️ Настройки профиля", reply_markup=profile_settings_kb())
    await message.answer("Пол пользователя:", reply_markup=profile_gender_kb(user.gender))
    await message.answer("Язык поиска:", reply_markup=language_kb(user.language))
    await message.answer("Кого искать:", reply_markup=gender_filter_kb(user.preferred_gender))
    await message.answer("Интересы:", reply_markup=interests_kb(selected_interests))


@router.message(lambda message: message.from_user and pending_profile_inputs.get(message.from_user.id) == "age")
async def set_age(message: Message) -> None:
    if not message.from_user:
        return

    text = (message.text or "").strip()
    if text.lower() in {"отмена", "cancel"}:
        pending_profile_inputs.pop(message.from_user.id, None)
        await message.answer("Изменение возраста отменено.")
        return

    if not text.isdigit():
        await message.answer("Введите возраст числом. Например: 21. Для отмены напишите «Отмена».")
        return

    age = int(text)
    if age < settings.MIN_AGE or age > settings.MAX_AGE:
        await message.answer(
            f"Возраст должен быть в диапазоне {settings.MIN_AGE}-{settings.MAX_AGE}. "
            "Для отмены напишите «Отмена»."
        )
        return

    pending_profile_inputs.pop(message.from_user.id, None)
    async with async_session() as session:
        await update_user(session, message.from_user.id, age=age)

    await message.answer(f"Возраст сохранен: {age}")
    await _send_profile(message)


@router.message(lambda message: message.from_user and pending_profile_inputs.get(message.from_user.id) == "status")
async def set_status(message: Message) -> None:
    if not message.from_user:
        return

    text = (message.text or "").strip()
    if text.lower() in {"отмена", "cancel"}:
        pending_profile_inputs.pop(message.from_user.id, None)
        await message.answer("Изменение статуса отменено.")
        return

    if len(text) > settings.STATUS_MAX_LENGTH:
        await message.answer(
            f"Статус слишком длинный. Максимум {settings.STATUS_MAX_LENGTH} символов. "
            "Для отмены напишите «Отмена»."
        )
        return

    pending_profile_inputs.pop(message.from_user.id, None)
    async with async_session() as session:
        await update_user(session, message.from_user.id, custom_status=text)

    await message.answer("Статус сохранен.")
    await _send_profile(message)


@router.message(F.text == "👑 Premium")
async def premium(message: Message) -> None:
    await message.answer(
        "👑 <b>Premium</b>\n\n"
        "• Быстрый поиск\n"
        "• Priority queue\n"
        "• Premium badge\n"
        "• Темы и кастомный профиль\n"
        "• Emoji профиля\n\n"
        "Пока премиум выдается вручную администратором."
    )
