import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _admin_ids() -> set[int]:
    return {
        int(value)
        for value in os.getenv("ADMIN_IDS", "").split(",")
        if value.strip().isdigit()
    }


@dataclass(frozen=True)
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
    ADMIN_IDS: set[int] = None

    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    REDIS_URL: str = os.getenv("REDIS_URL", "")

    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(400 * 1024 * 1024)))
    SPAM_COOLDOWN: float = float(os.getenv("SPAM_COOLDOWN", "0.7"))
    REMATCH_COOLDOWN: int = int(os.getenv("REMATCH_COOLDOWN", "3600"))
    LOW_QUALITY_REPUTATION: int = int(os.getenv("LOW_QUALITY_REPUTATION", "40"))
    REPORT_REPUTATION_PENALTY: int = int(os.getenv("REPORT_REPUTATION_PENALTY", "3"))
    MIN_AGE: int = int(os.getenv("MIN_AGE", "13"))
    MAX_AGE: int = int(os.getenv("MAX_AGE", "99"))
    STATUS_MAX_LENGTH: int = int(os.getenv("STATUS_MAX_LENGTH", "60"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __post_init__(self) -> None:
        object.__setattr__(self, "ADMIN_IDS", _admin_ids())
        if not self.BOT_TOKEN:
            raise RuntimeError("BOT_TOKEN is not set")

    @property
    def db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

        if all(
            [
                self.POSTGRES_HOST,
                self.POSTGRES_DB,
                self.POSTGRES_USER,
                self.POSTGRES_PASSWORD,
            ]
        ):
            return (
                "postgresql+asyncpg://"
                f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        return "sqlite+aiosqlite:///bot.db"


settings = Settings()
