from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings
from app.database.session import async_session
from app.services.reports import REPORT_CATEGORIES, mark_report_reviewed, pending_reports
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
        f"Банов: {data['banned']}\n"
        f"Shadow ban: {data['shadow']}\n"
        f"Сообщений в истории чатов: {data['chats']}\n"
        f"Жалоб всего: {data['reports']}\n"
        f"Жалоб без review: {data['pending_reports']}"
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


@router.message(Command("unban"))
async def unban(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /unban USER_ID")
        return

    async with async_session() as session:
        await update_user(session, int(parts[1]), banned=False, shadow_banned=False)

    await message.answer("Блокировка снята.")


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


@router.message(Command("review"))
async def review(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /review REPORT_ID")
        return

    async with async_session() as session:
        report = await mark_report_reviewed(session, int(parts[1]))

    if not report:
        await message.answer("Жалоба не найдена.")
        return

    await message.answer(f"Жалоба #{report.id} помечена как reviewed.")


@router.message(Command("premium"))
async def premium(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    parts = (message.text or "").split()
    if len(parts) != 3 or not parts[1].isdigit() or parts[2] not in {"on", "off"}:
        await message.answer("Использование: /premium USER_ID on|off")
        return

    async with async_session() as session:
        await update_user(session, int(parts[1]), premium=parts[2] == "on")

    await message.answer("Premium статус обновлен.")


@router.message(Command("admin"))
async def admin_panel(message: Message) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    await message.answer(
        "🛡 <b>Admin panel</b>\n\n"
        "/stats - статистика\n"
        "/reports - жалобы\n"
        "/ban USER_ID - бан\n"
        "/unban USER_ID - снять бан\n"
        "/shadowban USER_ID - shadow ban\n"
        "/review REPORT_ID - отметить жалобу\n"
        "/premium USER_ID on|off - premium"
    )
