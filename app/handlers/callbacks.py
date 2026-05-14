from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.database.session import async_session
from app.handlers.profile import pending_profile_inputs
from app.keyboards.inline import (
    INTERESTS,
    PROFILE_EMOJIS,
    PROFILE_THEMES,
    emoji_kb,
    gender_filter_kb,
    interests_kb,
    language_kb,
    profile_gender_kb,
    report_kb,
    theme_kb,
)
from app.services.reports import REPORT_CATEGORIES, create_report
from app.services.users import get_or_create_user, update_user
from app.config import settings


router = Router()


@router.callback_query(F.data.startswith("lang:"))
async def language(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    language_code = call.data.split(":", 1)[1]
    async with async_session() as session:
        await update_user(session, call.from_user.id, language=language_code)

    if call.message:
        await call.message.edit_reply_markup(reply_markup=language_kb(language_code))
    await call.answer("Язык сохранен")


@router.callback_query(F.data.startswith("pref_gender:"))
async def preferred_gender(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    value = call.data.split(":", 1)[1]
    async with async_session() as session:
        await update_user(session, call.from_user.id, preferred_gender=value)

    if call.message:
        await call.message.edit_reply_markup(reply_markup=gender_filter_kb(value))
    await call.answer("Фильтр сохранен")


@router.callback_query(F.data.startswith("gender:"))
async def profile_gender(call: CallbackQuery) -> None:
    if not call.from_user or call.data is None:
        return

    value = call.data.split(":", 1)[1]
    async with async_session() as session:
        await update_user(session, call.from_user.id, gender=value)

    if call.message:
        await call.message.edit_reply_markup(reply_markup=profile_gender_kb(value))
    await call.answer("Пол сохранен")


@router.callback_query(F.data.startswith("interest:"))
async def interest(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    key = call.data.split(":", 1)[1]
    async with async_session() as session:
        user = await get_or_create_user(session, call.from_user.id)
        selected = {item for item in user.interests.split(",") if item}
        if key in selected:
            selected.remove(key)
        else:
            selected.add(key)
        user.interests = ",".join(sorted(selected))
        await session.commit()

    if call.message:
        await call.message.edit_reply_markup(reply_markup=interests_kb(selected))
    await call.answer(f"Интерес: {INTERESTS.get(key, key)}")


@router.callback_query(F.data == "interest_done")
async def interest_done(call: CallbackQuery) -> None:
    await call.answer("Интересы сохранены")
    if call.message:
        await call.message.answer("Готово. Теперь можно искать собеседника.")


@router.callback_query(F.data.startswith("settings:"))
async def settings_actions(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    action = call.data.split(":", 1)[1]

    if action == "age":
        pending_profile_inputs[call.from_user.id] = "age"
        await call.answer()
        if call.message:
            await call.message.answer(
                f"Введите возраст числом от {settings.MIN_AGE} до {settings.MAX_AGE}. "
                "Для отмены напишите «Отмена»."
            )
        return

    if action == "status":
        pending_profile_inputs[call.from_user.id] = "status"
        await call.answer()
        if call.message:
            await call.message.answer(
                f"Введите новый статус до {settings.STATUS_MAX_LENGTH} символов. "
                "Для отмены напишите «Отмена»."
            )
        return

    async with async_session() as session:
        user = await get_or_create_user(session, call.from_user.id)
        if action == "emoji" and call.message:
            await call.message.answer("Выберите emoji профиля:", reply_markup=emoji_kb(user.profile_emoji))
        elif action == "theme" and call.message:
            await call.message.answer("Выберите theme профиля:", reply_markup=theme_kb(user.theme))
        elif action == "gender" and call.message:
            await call.message.answer("Выберите пол:", reply_markup=profile_gender_kb(user.gender))
        elif action == "status_clear":
            await update_user(session, call.from_user.id, custom_status="")
            await call.answer("Статус очищен")
            if call.message:
                await call.message.answer("Custom status очищен.")
            return

    await call.answer()


@router.callback_query(F.data.startswith("emoji:"))
async def emoji(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    value = call.data.split(":", 1)[1]
    if value not in PROFILE_EMOJIS:
        await call.answer("Неизвестный emoji", show_alert=True)
        return

    async with async_session() as session:
        await update_user(session, call.from_user.id, profile_emoji=value)

    if call.message:
        await call.message.edit_reply_markup(reply_markup=emoji_kb(value))
    await call.answer("Emoji сохранен")


@router.callback_query(F.data.startswith("theme:"))
async def theme(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    value = call.data.split(":", 1)[1]
    if value not in PROFILE_THEMES:
        await call.answer("Неизвестная theme", show_alert=True)
        return

    async with async_session() as session:
        await update_user(session, call.from_user.id, theme=value)

    if call.message:
        await call.message.edit_reply_markup(reply_markup=theme_kb(value))
    await call.answer("Theme сохранена")


@router.callback_query(F.data.startswith("rate:"))
async def rate(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    _, partner_id, reaction = call.data.split(":", 2)
    delta = 1 if reaction == "like" else -2

    async with async_session() as session:
        user = await get_or_create_user(session, int(partner_id))
        user.reputation = max(0, user.reputation + delta)
        await session.commit()

    await call.answer("Оценка сохранена")


@router.callback_query(F.data.startswith("report_menu:"))
async def report_menu(call: CallbackQuery) -> None:
    if not call.data or not call.message:
        return

    partner_id = int(call.data.split(":", 1)[1])
    await call.message.answer("Выберите причину жалобы:", reply_markup=report_kb(partner_id))
    await call.answer()


@router.callback_query(F.data.startswith("report:"))
async def report(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    _, partner_id, category = call.data.split(":", 2)
    async with async_session() as session:
        await create_report(session, call.from_user.id, int(partner_id), category)

    await call.answer("Жалоба отправлена")
    if call.message:
        await call.message.answer(f"🚨 Жалоба отправлена: {REPORT_CATEGORIES.get(category, category)}")
