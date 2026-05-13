import time

last_messages = {}

def check_spam(uid: int):
    now = time.time()

    last = last_messages.get(uid, 0)

    if now - last < 0.7:
        return False

    last_messages[uid] = now

    return True
