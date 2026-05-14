# Anonymous Chat Bot

Telegram anonymous chat bot for Railway.

## Railway variables

Set these variables in Railway:

```bash
BOT_TOKEN=your_botfather_token
ADMIN_IDS=123456789,987654321
```

`ADMIN_IDS` is optional. Do not commit real bot tokens to GitHub.

## Run locally

```bash
pip install -r requirements.txt
BOT_TOKEN=your_botfather_token python main.py
```

## Deploy

Railway uses the included `Dockerfile`.

