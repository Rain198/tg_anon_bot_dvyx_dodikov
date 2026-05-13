import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    ADMIN_IDS = [
        int(x)
        for x in os.getenv("ADMIN_IDS", "").split(",")
        if x.strip().isdigit()
    ]

    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

    REDIS_HOST = os.getenv("REDIS_HOST")
    REDIS_PORT = os.getenv("REDIS_PORT")

    MAX_FILE_SIZE = 400 * 1024 * 1024

settings = Settings()
