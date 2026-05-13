
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

MAX_FILE_SIZE = 400 * 1024 * 1024
SPAM_COOLDOWN = 0.7
