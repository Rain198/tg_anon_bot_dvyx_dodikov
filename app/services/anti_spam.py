import time

from app.config import settings


last_message_time: dict[int, float] = {}
flood_counter: dict[int, int] = {}


def check_spam(uid: int) -> bool:
    now = time.time()
    last = last_message_time.get(uid, 0)

    if now - last < settings.SPAM_COOLDOWN:
        flood_counter[uid] = flood_counter.get(uid, 0) + 1
        return False

    last_message_time[uid] = now
    flood_counter[uid] = 0
    return True
