from dataclasses import dataclass, field
from time import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ChatHistory, User
from app.services.cache import (
    get_active_partner,
    get_queue_member,
    get_queue_members,
    put_queue_member,
    remember_pair,
    remove_from_queues,
    set_active_pair,
    was_recent_pair,
    clear_active_pair,
)
from app.config import settings


@dataclass
class QueueMember:
    uid: int
    language: str
    gender: str
    preferred_gender: str
    interests: set[str]
    reputation: int
    premium: bool
    shadow_banned: bool
    joined_at: float = field(default_factory=time)


def _interests(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _queue_name(user: User) -> str:
    if user.shadow_banned:
        return "shadow"
    if user.reputation < settings.LOW_QUALITY_REPUTATION:
        return "low_quality"
    if user.premium:
        return "premium"
    return "regular"


async def enqueue(user: User) -> None:
    member = QueueMember(
        uid=user.uid,
        language=user.language,
        gender=user.gender,
        preferred_gender=user.preferred_gender,
        interests=_interests(user.interests),
        reputation=user.reputation,
        premium=user.premium,
        shadow_banned=user.shadow_banned,
    )
    await put_queue_member(
        _queue_name(user),
        {
            "uid": member.uid,
            "language": member.language,
            "gender": member.gender,
            "preferred_gender": member.preferred_gender,
            "interests": sorted(member.interests),
            "reputation": member.reputation,
            "premium": member.premium,
            "shadow_banned": member.shadow_banned,
            "joined_at": member.joined_at,
        },
    )


def _gender_ok(left: QueueMember, right: QueueMember) -> bool:
    left_ok = left.preferred_gender in ("", "any") or (
        right.gender and left.preferred_gender == right.gender
    )
    right_ok = right.preferred_gender in ("", "any") or (
        left.gender and right.preferred_gender == left.gender
    )
    return left_ok and right_ok


def _from_payload(payload: dict[str, object]) -> QueueMember:
    return QueueMember(
        uid=int(payload["uid"]),
        language=str(payload["language"]),
        gender=str(payload["gender"]),
        preferred_gender=str(payload["preferred_gender"]),
        interests=set(payload["interests"]),
        reputation=int(payload["reputation"]),
        premium=bool(payload["premium"]),
        shadow_banned=bool(payload["shadow_banned"]),
        joined_at=float(payload.get("joined_at", time())),
    )


def _match_score(left: QueueMember, right: QueueMember) -> int | None:
    if left.language != right.language:
        return None
    if not _gender_ok(left, right):
        return None

    common_interests = left.interests & right.interests
    score = 100
    score += len(common_interests) * 15
    score -= abs(left.reputation - right.reputation)
    score += max(0, 20 - int(time() - right.joined_at))
    if left.premium and right.premium:
        score += 10
    return score


async def _queue_for_user(uid: int) -> tuple[str, QueueMember] | None:
    payload = await get_queue_member(uid)
    if not payload:
        return None

    member = _from_payload(payload)
    if member.shadow_banned:
        return "shadow", member
    if member.reputation < settings.LOW_QUALITY_REPUTATION:
        return "low_quality", member
    if member.premium:
        return "premium_regular", member
    return "premium_regular", member


async def _candidate_members(queue_group: str) -> list[QueueMember]:
    queue_names = {
        "shadow": ("shadow",),
        "low_quality": ("low_quality",),
        "premium_regular": ("premium", "regular"),
    }[queue_group]

    members: list[QueueMember] = []
    for queue_name in queue_names:
        payloads = await get_queue_members(queue_name)
        members.extend(_from_payload(payload) for payload in payloads)
    return members


async def try_match(session: AsyncSession, uid: int) -> tuple[int, int] | None:
    current = await _queue_for_user(uid)
    if not current:
        return None

    queue_group, member = current
    if await get_active_partner(uid):
        return None

    candidates = [
        item
        for item in await _candidate_members(queue_group)
        if item.uid != uid and not await get_active_partner(item.uid)
    ]

    scored: list[tuple[QueueMember, int]] = []
    for candidate in candidates:
        if await was_recent_pair(member.uid, candidate.uid):
            continue
        score = _match_score(member, candidate)
        if score is not None:
            scored.append((candidate, score))

    if not scored:
        return None

    partner = max(scored, key=lambda item: item[1])[0]
    await set_active_pair(uid, partner.uid)
    await remove_from_queues(uid)
    await remove_from_queues(partner.uid)
    await remember_pair(uid, partner.uid)

    first = await session.get(User, uid)
    second = await session.get(User, partner.uid)
    if first:
        first.chats_count += 1
    if second:
        second.chats_count += 1

    session.add(ChatHistory(user_id=uid, partner_id=partner.uid))
    session.add(ChatHistory(user_id=partner.uid, partner_id=uid))
    await session.commit()
    return uid, partner.uid


async def get_partner(uid: int) -> int | None:
    return await get_active_partner(uid)


async def stop_chat(uid: int) -> int | None:
    partner = await clear_active_pair(uid)
    await remove_from_queues(uid)
    return partner
