import random


answers: dict[int, int] = {}


def create_captcha(uid: int) -> str:
    left = random.randint(1, 9)
    right = random.randint(1, 9)
    answers[uid] = left + right
    return f"🤖 Проверка\n\nСколько будет {left} + {right}?"


def verify_captcha(uid: int, text: str | None) -> bool:
    if not text or not text.isdigit():
        return False

    ok = int(text) == answers.get(uid)
    if ok:
        answers.pop(uid, None)
    return ok
