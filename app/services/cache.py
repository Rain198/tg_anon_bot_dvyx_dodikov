import asyncio
import json
import time
from typing import Any

from redis.asyncio import Redis

from app.config import settings


redis: Redis | None = Redis.from_url(settings.REDIS_URL, decode_responses=True) if settings.REDIS_URL else None
runtime_lock = asyncio.Lock()

QUEUE_NAMES = ("regular", "premium", "low_quality", "shadow")

_memory_online: dict[int, float] = {}
_memory_members: dict[int, dict[str, Any]] = {}
_memory_queues: dict[str, list[int]] = {name: [] for name in QUEUE_NAMES}
_memory_pairs: dict[int, int] = {}
_memory_recent_pairs: dict[str, float] = {}


def _member_key(uid: int) -> str:
    return f"match:member:{uid}"


def _queue_key(name: str) -> str:
    return f"match:queue:{name}"


def _recent_key(uid1: int, uid2: int) -> str:
    left, right = sorted((uid1, uid2))
    return f"{left}:{right}"


async def _cleanup_recent_memory() -> None:
    now = time.time()
    expired = [
        key
        for key, expires_at in _memory_recent_pairs.items()
        if expires_at <= now
    ]
    for key in expired:
        _memory_recent_pairs.pop(key, None)


async def set_online(uid: int) -> None:
    if redis:
        await redis.setex(f"online:{uid}", 300, "1")
        return

    async with runtime_lock:
        _memory_online[uid] = time.time() + 300


async def is_online(uid: int) -> bool:
    if redis:
        return bool(await redis.exists(f"online:{uid}"))

    async with runtime_lock:
        expires_at = _memory_online.get(uid)
        if not expires_at:
            return False
        if expires_at <= time.time():
            _memory_online.pop(uid, None)
            return False
        return True


async def remove_online(uid: int) -> None:
    if redis:
        await redis.delete(f"online:{uid}")
        return

    async with runtime_lock:
        _memory_online.pop(uid, None)


async def remove_from_queues(uid: int) -> None:
    if redis:
        member_key = _member_key(uid)
        pipe = redis.pipeline()
        pipe.delete(member_key)
        for queue_name in QUEUE_NAMES:
            pipe.lrem(_queue_key(queue_name), 0, str(uid))
        await pipe.execute()
        return

    async with runtime_lock:
        _memory_members.pop(uid, None)
        for queue_name in QUEUE_NAMES:
            _memory_queues[queue_name] = [
                member_uid for member_uid in _memory_queues[queue_name] if member_uid != uid
            ]


async def put_queue_member(queue_name: str, member: dict[str, Any]) -> None:
    uid = int(member["uid"])
    await remove_from_queues(uid)

    if redis:
        pipe = redis.pipeline()
        pipe.set(_member_key(uid), json.dumps(member, ensure_ascii=True))
        pipe.rpush(_queue_key(queue_name), str(uid))
        await pipe.execute()
        return

    async with runtime_lock:
        _memory_members[uid] = member
        _memory_queues[queue_name].append(uid)


async def get_queue_members(queue_name: str) -> list[dict[str, Any]]:
    if redis:
        ids = await redis.lrange(_queue_key(queue_name), 0, -1)
        members: list[dict[str, Any]] = []
        for raw_uid in ids:
            payload = await redis.get(_member_key(int(raw_uid)))
            if payload:
                members.append(json.loads(payload))
        return members

    async with runtime_lock:
        return [
            _memory_members[uid]
            for uid in _memory_queues[queue_name]
            if uid in _memory_members
        ]


async def get_queue_member(uid: int) -> dict[str, Any] | None:
    if redis:
        payload = await redis.get(_member_key(uid))
        return json.loads(payload) if payload else None

    async with runtime_lock:
        return _memory_members.get(uid)


async def set_active_pair(uid: int, partner_uid: int) -> None:
    if redis:
        await redis.hset("match:active_pairs", mapping={str(uid): partner_uid, str(partner_uid): uid})
        return

    async with runtime_lock:
        _memory_pairs[uid] = partner_uid
        _memory_pairs[partner_uid] = uid


async def get_active_partner(uid: int) -> int | None:
    if redis:
        value = await redis.hget("match:active_pairs", str(uid))
        return int(value) if value else None

    async with runtime_lock:
        return _memory_pairs.get(uid)


async def clear_active_pair(uid: int) -> int | None:
    if redis:
        partner = await get_active_partner(uid)
        if not partner:
            return None

        await redis.hdel("match:active_pairs", str(uid), str(partner))
        return partner

    async with runtime_lock:
        partner = _memory_pairs.pop(uid, None)
        if partner:
            _memory_pairs.pop(partner, None)
        return partner


async def remember_pair(uid1: int, uid2: int) -> None:
    pair_key = _recent_key(uid1, uid2)
    ttl = settings.REMATCH_COOLDOWN

    if redis:
        await redis.setex(f"match:recent:{pair_key}", ttl, "1")
        return

    async with runtime_lock:
        _memory_recent_pairs[pair_key] = time.time() + ttl


async def was_recent_pair(uid1: int, uid2: int) -> bool:
    pair_key = _recent_key(uid1, uid2)

    if redis:
        return bool(await redis.exists(f"match:recent:{pair_key}"))

    async with runtime_lock:
        await _cleanup_recent_memory()
        expires_at = _memory_recent_pairs.get(pair_key)
        return bool(expires_at and expires_at > time.time())


async def close_cache() -> None:
    if redis:
        await redis.aclose()
