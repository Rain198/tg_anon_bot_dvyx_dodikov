# SINGLE FILE ANONYMOUS CHAT BOT

import os
import time
import random
import sqlite3
import logging
from dataclasses import dataclass, field
from typing import Optional

import telebot
from telebot import types

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8847730026:AAE2w2AByxiSRXCPSssP5QsT5QsdBgapHzk")

_raw_admins = os.getenv("ADMIN_IDS", "5428663703,8484221382")

ADMIN_IDS = {
    int(x)
    for x in _raw_admins.split(",")
    if x.strip().isdigit()
}

MAX_FILE_SIZE = 400 * 1024 * 1024

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# =====================================================
# SQLITE
# =====================================================

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    uid INTEGER PRIMARY KEY,
    gender TEXT,
    age INTEGER,
    language TEXT,
    premium INTEGER DEFAULT 0,
    reputation INTEGER DEFAULT 100
)
''')

conn.commit()

# =====================================================
# DATA
# =====================================================

REACTIONS = ["👍", "👎", "🤷", "💫", "🔥"]

INTERESTS = [
    "🎮 Игры",
    "🎵 Музыка",
    "💕 Отношения",
    "💻 IT",
    "🎬 Фильмы",
    "😈 Флирт",
]

REPORT_TYPES = {
    "spam": "🧻 Спам и реклама",
    "sale": "💰 Продажа",
    "hate": "⛔ Разжигание розни",
    "cp": "🔞 Детская порнография",
    "beg": "🥺 Попрошайничество",
    "insult": "🤬 Оскорбление",
    "violence": "👊 Насилие",
    "suicide": "📢 Пропаганда суицида",
    "nsfw": "❌ Пошлый собеседник",
    "minor": "🔞 Несовершеннолетний",
}


@dataclass
class Profile:
    uid: int

    gender: str = ""
    age: int = 0

    language: str = "ru"

    interests: list = field(default_factory=list)

    premium: bool = False

    reputation: int = 100

    banned: bool = False

    shadow_banned: bool = False

    registered: bool = False

    profile_theme: str = "default"

    custom_status: str = ""

    profile_emoji: str = "⭐"

    reactions: dict = field(default_factory=lambda: {
        r: 0 for r in REACTIONS
    })

    chats_count: int = 0


profiles = {}

pairs = {}

waiting = []

premium_waiting = []

low_quality_waiting = []

reg_state = {}

last_message_time = {}

spam_counter = {}

captcha_answers = {}

# =====================================================
# HELPERS
# =====================================================


def get_profile(uid):
    if uid not in profiles:
        profiles[uid] = Profile(uid=uid)

    return profiles[uid]



def anti_spam(uid):
    now = time.time()

    last = last_message_time.get(uid, 0)

    if now - last < 0.7:
        spam_counter[uid] = spam_counter.get(uid, 0) + 1
        return False

    last_message_time[uid] = now

    return True



def premium_badge(profile):
    return "👑" if profile.premium else ""



def send_captcha(uid):
    a = random.randint(1, 9)
    b = random.randint(1, 9)

    captcha_answers[uid] = a + b

    bot.send_message(
        uid,
        f"🤖 Проверка\n\nСколько будет {a} + {b}?"
    )



def try_match():
    queue = premium_waiting + waiting

    i = 0

    while i < len(queue):
        uid1 = queue[i]

        if i + 1 >= len(queue):
            break

        uid2 = queue[i + 1]

        p1 = get_profile(uid1)
        p2 = get_profile(uid2)

        if p1.language != p2.language:
            i += 1
            continue

        pairs[uid1] = uid2
        pairs[uid2] = uid1

        try:
            bot.send_message(uid1, "✅ Собеседник найден")
            bot.send_message(uid2, "✅ Собеседник найден")
        except:
            pass

        if uid1 in premium_waiting:
            premium_waiting.remove(uid1)
        if uid2 in premium_waiting:
            premium_waiting.remove(uid2)

        if uid1 in waiting:
            waiting.remove(uid1)
        if uid2 in waiting:
            waiting.remove(uid2)

        i += 2

# =====================================================
# KEYBOARDS
# =====================================================


def kb_main():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("🔍 Найти", "🛑 Стоп")

    kb.row("👤 Профиль", "👑 Premium")

    return kb



def kb_language():
    kb = types.InlineKeyboardMarkup()

    kb.row(
        types.InlineKeyboardButton(
            "🇷🇺 Русский",
            callback_data="lang:ru"
        ),
        types.InlineKeyboardButton(
            "🇺🇸 English",
            callback_data="lang:en"
        )
    )

    return kb



def kb_reports_main():
    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton("👍", callback_data="rate:like"),
        types.InlineKeyboardButton("👎", callback_data="rate:dislike")
    )

    kb.add(types.InlineKeyboardButton(
        "🧻 Спам и реклама",
        callback_data="report:spam"
    ))

    kb.add(types.InlineKeyboardButton(
        "❌ Пошлый собеседник",
        callback_data="report:nsfw"
    ))

    kb.add(types.InlineKeyboardButton(
        "🔞 Несовершеннолетний",
        callback_data="report:minor"
    ))

    kb.add(types.InlineKeyboardButton(
        "⚠️ Другая жалоба",
        callback_data="report_more"
    ))

    return kb

# =====================================================
# COMMANDS
# =====================================================


@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id

    p = get_profile(uid)

    if p.banned:
        bot.send_message(uid, "🚫 Вы заблокированы")
        return

    if not p.registered:
        reg_state[uid] = "captcha"
        send_captcha(uid)
        return

    bot.send_message(
        uid,
        "Добро пожаловать",
        reply_markup=kb_main()
    )


@bot.message_handler(commands=["profile"])
def profile(msg):
    uid = msg.from_user.id

    p = get_profile(uid)

    premium = "👑 PREMIUM" if p.premium else "🆓 FREE"

    text = (
        f"{p.profile_emoji} Профиль\n\n"
        f"{premium}\n"
        f"Репутация: {p.reputation}\n"
        f"Чатов: {p.chats_count}\n"
        f"Статус: {p.custom_status}"
    )

    bot.send_message(uid, text)


@bot.message_handler(commands=["stats"])
def stats(msg):
    total_users = len(profiles)

    premium_users = sum(
        1 for p in profiles.values()
        if p.premium
    )

    text = (
        f"👥 Пользователей: {total_users}\n"
        f"👑 Premium: {premium_users}"
    )

    bot.send_message(msg.chat.id, text)

# =====================================================
# BUTTONS
# =====================================================


@bot.message_handler(func=lambda m: m.text == "🔍 Найти")
def find(msg):
    uid = msg.from_user.id

    p = get_profile(uid)

    if p.shadow_banned:
        bot.send_message(uid, "🔍 Ищем собеседника...")
        return

    if p.reputation < 40:
        low_quality_waiting.append(uid)
        bot.send_message(uid, "🔍 Поиск...")
        return

    if p.premium:
        premium_waiting.append(uid)
    else:
        waiting.append(uid)

    bot.send_message(uid, "🔍 Ищем собеседника")

    try_match()


@bot.message_handler(func=lambda m: m.text == "🛑 Стоп")
def stop(msg):
    uid = msg.from_user.id

    partner = pairs.get(uid)

    if partner:
        del pairs[uid]
        del pairs[partner]

        bot.send_message(uid, "🛑 Чат завершён")
        bot.send_message(partner, "🛑 Чат завершён")


@bot.message_handler(func=lambda m: m.text == "👑 Premium")
def premium(msg):
    text = (
        "👑 PREMIUM\n\n"
        "• Быстрый поиск\n"
        "• Premium badge\n"
        "• Кастом профиль\n"
        "• Темы\n"
        "• Приоритет в очереди"
    )

    bot.send_message(msg.chat.id, text)

# =====================================================
# CALLBACKS
# =====================================================


@bot.callback_query_handler(func=lambda c: c.data.startswith("lang:"))
def lang(call):
    uid = call.from_user.id

    language = call.data.split(":")[1]

    p = get_profile(uid)

    p.language = language

    bot.answer_callback_query(call.id, "Язык сохранён")


@bot.callback_query_handler(func=lambda c: c.data.startswith("report:"))
def report(call):
    uid = call.from_user.id

    report_type = call.data.split(":")[1]

    p = get_profile(uid)

    p.reputation -= 1

    bot.answer_callback_query(call.id)

    bot.send_message(
        uid,
        f"🚨 Жалоба отправлена: {REPORT_TYPES.get(report_type)}"
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("rate:"))
def rate(call):
    uid = call.from_user.id

    reaction = call.data.split(":")[1]

    p = get_profile(uid)

    if reaction == "like":
        p.reputation += 1

    if reaction == "dislike":
        p.reputation -= 2

    bot.answer_callback_query(call.id, "Оценка сохранена")

# =====================================================
# TEXT
# =====================================================


@bot.message_handler(content_types=["text"])
def text(msg):
    uid = msg.from_user.id

    if reg_state.get(uid) == "captcha":
        if not msg.text.isdigit():
            return

        if int(msg.text) != captcha_answers.get(uid):
            bot.send_message(uid, "❌ Неверно")
            return

        reg_state.pop(uid)

        p = get_profile(uid)

        p.registered = True

        bot.send_message(
            uid,
            "✅ Регистрация завершена",
            reply_markup=kb_main()
        )

        return

    if not anti_spam(uid):
        return

    partner = pairs.get(uid)

    if not partner:
        return

    try:
        bot.send_message(partner, msg.text)
    except:
        pass

# =====================================================
# MEDIA
# =====================================================


@bot.message_handler(content_types=["video"])
def relay_video(msg):
    uid = msg.from_user.id

    if msg.video.file_size > MAX_FILE_SIZE:
        bot.send_message(uid, "❌ Максимальный размер файла 400MB")
        return

    partner = pairs.get(uid)

    if not partner:
        return

    bot.send_video(
        partner,
        msg.video.file_id,
        caption=msg.caption,
        reply_markup=kb_reports_main()
    )


@bot.message_handler(content_types=["document"])
def relay_document(msg):
    uid = msg.from_user.id

    if msg.document.file_size > MAX_FILE_SIZE:
        bot.send_message(uid, "❌ Максимальный размер файла 400MB")
        return

    partner = pairs.get(uid)

    if not partner:
        return

    bot.send_document(partner, msg.document.file_id)


@bot.message_handler(content_types=["photo"])
def relay_photo(msg):
    uid = msg.from_user.id

    partner = pairs.get(uid)

    if not partner:
        return

    bot.send_photo(
        partner,
        msg.photo[-1].file_id,
        caption=msg.caption,
        reply_markup=kb_reports_main()
    )

# =====================================================
# START
# =====================================================

print("Bot started...")

bot.infinity_polling(timeout=30, long_polling_timeout=30)
```
