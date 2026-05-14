from dataclasses import dataclass, field
from time import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ChatHistory, User


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


waiting: list[QueueMember] = []
premium_waiting: list[QueueMember] = []
low_quality_waiting: list[QueueMember] = []
shadow_waiting: set[int] = set()
active_pairs: dict[int, int] = {}
recent_pairs: set[tuple[int, int]] = set()


def _pair_key(uid1: int, uid2: int) -> tuple[int, int]:
    return tuple(sorted((uid1, uid2)))


def _interests(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def remove_from_queue(uid: int) -> None:
    global waiting, premium_waiting, low_quality_waiting
    waiting = [member for member in waiting if member.uid != uid]
    premium_waiting = [member for member in premium_waiting if member.uid != uid]
    low_quality_waiting = [member for member in low_quality_waiting if member.uid != uid]
    shadow_waiting.discard(uid)


def enqueue(user: User) -> None:
    remove_from_queue(user.uid)

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

    if user.shadow_banned:
        shadow_waiting.add(user.uid)
    elif user.reputation < 40:
        low_quality_waiting.append(member)
    elif user.premium:
        premium_waiting.append(member)
    else:
        waiting.append(member)


def _gender_ok(left: QueueMember, right: QueueMember) -> bool:
    left_ok = left.preferred_gender in ("", "any", right.gender)
    right_ok = right.preferred_gender in ("", "any", left.gender)
    return left_ok and right_ok


def _match_score(left: QueueMember, right: QueueMember) -> int:
    if left.language != right.language:
        return -1
    if not _gender_ok(left, right):
        return -1
    if _pair_key(left.uid, right.uid) in recent_pairs:
        return -1

    common_interests = left.interests & right.interests
    reputation_delta = abs(left.reputation - right.reputation)
    return len(common_interests) * 10 - reputation_delta


async def try_match(session: AsyncSession, uid: int) -> tuple[int, int] | None:
    queue = premium_waiting + waiting
    member = next((item for item in queue if item.uid == uid), None)
    if not member:
        queue = low_quality_waiting
        member = next((item for item in queue if item.uid == uid), None)

    if not member or uid in active_pairs:
        return None

    candidates = [item for item in queue if item.uid != uid and item.uid not in active_pairs]
    scored = [(candidate, _match_score(member, candidate)) for candidate in candidates]
    scored = [(candidate, score) for candidate, score in scored if score >= -20]
    if not scored:
        return None

    partner = max(scored, key=lambda item: item[1])[0]
    active_pairs[uid] = partner.uid
    active_pairs[partner.uid] = uid
    remove_from_queue(uid)
    remove_from_queue(partner.uid)
    recent_pairs.add(_pair_key(uid, partner.uid))

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


def get_partner(uid: int) -> int | None:
    return active_pairs.get(uid)


def stop_chat(uid: int) -> int | None:
    partner = active_pairs.pop(uid, None)
    if partner:
        active_pairs.pop(partner, None)
    remove_from_queue(uid)
    return partner
