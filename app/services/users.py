from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


async def get_or_create_user(session: AsyncSession, uid: int) -> User:
    user = await session.get(User, uid)
    if user:
        return user

    user = User(uid=uid)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user(session: AsyncSession, uid: int, **values) -> User:
    user = await get_or_create_user(session, uid)
    for key, value in values.items():
        if hasattr(user, key):
            setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user


async def stats(session: AsyncSession) -> dict[str, int]:
    total = await session.scalar(select(func.count(User.uid)))
    premium = await session.scalar(select(func.count(User.uid)).where(User.premium.is_(True)))
    banned = await session.scalar(select(func.count(User.uid)).where(User.banned.is_(True)))
    return {
        "total": total or 0,
        "premium": premium or 0,
        "banned": banned or 0,
    }
