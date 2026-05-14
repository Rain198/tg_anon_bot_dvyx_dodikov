from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings
from app.database.session import async_session
from app.services.reports import REPORT_CATEGORIES, pending_reports
from app.services.users import stats, update_user


router = Router()


def _is_admin(uid: int | None) -> bool:
    return bool(uid and uid in settings.ADMIN_IDS)


@router.message(Command("stats"))
async def admin_stats(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    async with async_session() as session:
        data = await stats(session)

    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"Пользователей: {data['total']}\n"
        f"Premium: {data['premium']}\n"
        f"Банов: {data['banned']}"
    )


@router.message(Command("reports"))
async def admin_reports(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    async with async_session() as session:
        reports = await pending_reports(session)

    if not reports:
        await message.answer("Новых жалоб нет.")
        return

    lines = ["🚨 <b>Последние жалобы</b>"]
    for report in reports:
        label = REPORT_CATEGORIES.get(report.category, report.category)
        lines.append(f"#{report.id}: {report.reporter_id} -> {report.reported_id}: {label}")

    await message.answer("\n".join(lines))


@router.message(Command("ban"))
async def ban(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban USER_ID")
        return

    async with async_session() as session:
        await update_user(session, int(parts[1]), banned=True)

    await message.answer("Пользователь забанен.")


@router.message(Command("shadowban"))
async def shadowban(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /shadowban USER_ID")
        return

    async with async_session() as session:
        await update_user(session, int(parts[1]), shadow_banned=True)

    await message.answer("Shadow ban включен.")


@router.message(F.text == "/admin")
async def admin_panel(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        "🛡 <b>Admin panel</b>\n\n"
        "/stats - статистика\n"
        "/reports - жалобы\n"
        "/ban USER_ID - бан\n"
        "/shadowban USER_ID - shadow ban"
    )
