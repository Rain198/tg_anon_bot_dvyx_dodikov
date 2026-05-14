from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Report, User


REPORT_CATEGORIES = {
    "spam": "Спам и реклама",
    "sale": "Продажа",
    "hate": "Разжигание розни",
    "cp": "Детская порнография",
    "beg": "Попрошайничество",
    "insult": "Оскорбление",
    "violence": "Насилие",
    "suicide": "Пропаганда суицида",
    "nsfw": "Пошлый собеседник",
    "minor": "Несовершеннолетний",
}


async def create_report(
    session: AsyncSession,
    reporter_id: int,
    reported_id: int,
    category: str,
) -> Report:
    report = Report(
        reporter_id=reporter_id,
        reported_id=reported_id,
        category=category,
    )
    session.add(report)

    user = await session.get(User, reported_id)
    if user:
        user.reputation = max(0, user.reputation - settings.REPORT_REPUTATION_PENALTY)

    await session.commit()
    await session.refresh(report)
    return report


async def pending_reports(session: AsyncSession) -> list[Report]:
    result = await session.scalars(
        select(Report).where(Report.reviewed.is_(False)).order_by(Report.created_at.desc()).limit(10)
    )
    return list(result)


async def mark_report_reviewed(session: AsyncSession, report_id: int) -> Report | None:
    report = await session.get(Report, report_id)
    if not report:
        return None

    report.reviewed = True
    await session.commit()
    await session.refresh(report)
    return report
