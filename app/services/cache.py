from redis.asyncio import Redis

from app.config import settings


redis: Redis | None = Redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None


async def set_online(uid: int) -> None:
    if redis:
        await redis.setex(f"online:{uid}", 300, "1")


async def is_online(uid: int) -> bool:
    if not redis:
        return True
    return bool(await redis.exists(f"online:{uid}"))


async def close_cache() -> None:
    if redis:
        await redis.aclose()
