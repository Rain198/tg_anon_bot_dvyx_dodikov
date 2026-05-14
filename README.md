# TG Anon Bot

Anonymous Telegram chat bot with profiles, matchmaking, moderation, anti-spam, Redis-backed runtime state, PostgreSQL support, and Railway/Docker deployment.

## Features

- Anonymous 1-to-1 chat with `find`, `next`, and `stop`
- Relay for text, photo, video, voice, video note, stickers, documents, and audio
- CAPTCHA on onboarding
- Profile with gender, age, interests, reputation, emoji, custom status, and theme
- Matchmaking by language, gender preference, interests, premium priority, reputation, and anti-rematch cooldown
- Report flow with moderation categories and automatic reputation penalty
- Admin commands for stats, bans, shadow bans, report review, and premium management
- PostgreSQL with SQLite fallback
- Redis support for online state, active pairs, and queue runtime data

## Environment

Copy `env.example` to `.env` and set at least:

```bash
BOT_TOKEN=your_botfather_token
ADMIN_IDS=123456789,987654321
```

Important variables:

- `DATABASE_URL` or `POSTGRES_*` for the database
- `REDIS_URL` for runtime matchmaking state
- `REMATCH_COOLDOWN` to prevent immediate rematches
- `LOW_QUALITY_REPUTATION` to isolate low-reputation users
- `REPORT_REPUTATION_PENALTY` for auto reputation decrease after reports

`ADMIN_IDS` is optional. Never commit a real bot token.

## Local run

```bash
pip install -r requirements.txt
python main.py
```

The bot loads variables from `.env` automatically.

## Docker

```bash
docker compose up --build
```

This starts:

- bot
- PostgreSQL
- Redis

## Railway

The repository is ready for Railway deployment through the included `Dockerfile`.
