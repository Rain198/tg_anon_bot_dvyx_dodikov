from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.database.session import async_session
from app.keyboards.inline import INTERESTS, report_kb
from app.services.reports import REPORT_CATEGORIES, create_report
from app.services.users import get_or_create_user, update_user


router = Router()


@router.callback_query(F.data.startswith("lang:"))
async def language(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    language_code = call.data.split(":", 1)[1]
    async with async_session() as session:
        await update_user(session, call.from_user.id, language=language_code)

    await call.answer("Язык сохранен")


@router.callback_query(F.data.startswith("pref_gender:"))
async def preferred_gender(call: CallbackQuery) -> None:
    if not call.from_user or not call.data:
        return

    value = call.data.split(":", 1)[1]
    async with async_session() as session:
        await update_user(session, call.from_user.id, preferred_gender=value)

    await call.answer("Фильтр сохранен")


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

    await call.answer(f"Интерес: {INTERESTS.get(key, key)}")


@router.callback_query(F.data == "interest_done")
async def interest_done(call: CallbackQuery) -> None:
    await call.answer("Интересы сохранены")
    if call.message:
        await call.message.answer("Готово. Теперь можно искать собеседника.")


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
