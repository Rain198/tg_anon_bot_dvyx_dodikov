"""
Telegram Anonymous Chat Bot
----------------------------
Команды:
  /start  — начать / войти в поиск собеседника
  /stop   — завершить текущий диалог
  /next   — найти нового собеседника (сбрасывает текущий чат)
  /help   — список команд

Зависимости:
  pip install pyTelegramBotAPI

Запуск:
  BOT_TOKEN=<твой_токен> python anon_chat_bot.py
  или вставь токен прямо в переменную BOT_TOKEN ниже.
"""

import os
import logging
import telebot
from telebot import types

# ─── Настройки ────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8847730026:AAE2w2AByxiSRXCPSssP5QsT5QsdBgapHzk")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ─── Хранилище состояний (в памяти) ───────────────────────────────────────────
# waiting  — список user_id, ожидающих пару
# pairs    — {user_id: partner_id}
waiting: list[int] = []
pairs: dict[int, int] = {}


# ─── Вспомогательные функции ──────────────────────────────────────────────────

def in_chat(uid: int) -> bool:
    return uid in pairs


def in_queue(uid: int) -> bool:
    return uid in waiting


def remove_from_queue(uid: int) -> None:
    if uid in waiting:
        waiting.remove(uid)


def disconnect(uid: int) -> None:
    """Разорвать пару для uid (и партнёра)."""
    partner = pairs.pop(uid, None)
    if partner:
        pairs.pop(partner, None)
        try:
            bot.send_message(partner, "🔴 Собеседник покинул чат.\n\n"
                                      "Нажми /start чтобы найти нового.")
        except Exception:
            pass


def try_match() -> None:
    """Если в очереди >= 2 человека — соединить первых двух."""
    while len(waiting) >= 2:
        u1 = waiting.pop(0)
        u2 = waiting.pop(0)
        pairs[u1] = u2
        pairs[u2] = u1
        msg = ("✅ Собеседник найден! Можете общаться анонимно.\n\n"
               "/stop — завершить чат\n/next — новый собеседник")
        try:
            bot.send_message(u1, msg)
            bot.send_message(u2, msg)
            log.info("Matched %s <-> %s", u1, u2)
        except Exception as e:
            log.warning("Match error: %s", e)


def main_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 Найти собеседника", "⏭ Следующий")
    kb.row("🛑 Стоп", "❓ Помощь")
    return kb


# ─── Обработчики команд ───────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(msg: types.Message) -> None:
    uid = msg.from_user.id

    if in_chat(uid):
        bot.send_message(uid, "Ты уже в чате. /stop чтобы выйти.", reply_markup=main_keyboard())
        return

    if in_queue(uid):
        bot.send_message(uid, "⏳ Уже ищем собеседника, подожди...", reply_markup=main_keyboard())
        return

    waiting.append(uid)
    log.info("User %s joined queue (queue size: %s)", uid, len(waiting))
    bot.send_message(
        uid,
        "👋 Привет! Ищем тебе собеседника...\n\n"
        "Это анонимный чат — никто не узнает кто ты.",
        reply_markup=main_keyboard(),
    )
    try_match()


@bot.message_handler(commands=["stop"])
def cmd_stop(msg: types.Message) -> None:
    uid = msg.from_user.id

    if in_chat(uid):
        disconnect(uid)
        bot.send_message(uid, "🔴 Чат завершён. Нажми /start чтобы найти нового собеседника.",
                         reply_markup=main_keyboard())
        return

    if in_queue(uid):
        remove_from_queue(uid)
        bot.send_message(uid, "❌ Поиск отменён.", reply_markup=main_keyboard())
        return

    bot.send_message(uid, "Ты не в чате. Нажми /start чтобы начать.", reply_markup=main_keyboard())


@bot.message_handler(commands=["next"])
def cmd_next(msg: types.Message) -> None:
    uid = msg.from_user.id

    if in_chat(uid):
        disconnect(uid)
        bot.send_message(uid, "🔄 Ищем нового собеседника...")
    elif in_queue(uid):
        bot.send_message(uid, "⏳ Уже ищем... подожди.")
        return
    else:
        bot.send_message(uid, "🔄 Ищем собеседника...")

    waiting.append(uid)
    try_match()


@bot.message_handler(commands=["help"])
def cmd_help(msg: types.Message) -> None:
    text = (
        "📖 *Команды:*\n"
        "/start — найти собеседника\n"
        "/stop  — завершить чат\n"
        "/next  — новый собеседник\n"
        "/help  — это сообщение\n\n"
        "Чат полностью анонимный. Никакие данные не хранятся."
    )
    bot.send_message(msg.from_user.id, text, parse_mode="Markdown", reply_markup=main_keyboard())


# ─── Кнопки клавиатуры ────────────────────────────────────────────────────────

BUTTON_MAP = {
    "🔍 Найти собеседника": cmd_start,
    "⏭ Следующий": cmd_next,
    "🛑 Стоп": cmd_stop,
    "❓ Помощь": cmd_help,
}


@bot.message_handler(func=lambda m: m.text in BUTTON_MAP)
def handle_buttons(msg: types.Message) -> None:
    BUTTON_MAP[msg.text](msg)


# ─── Пересылка сообщений ──────────────────────────────────────────────────────

@bot.message_handler(content_types=["text"])
def relay_text(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)

    if partner is None:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.",
                         reply_markup=main_keyboard())
        return

    try:
        bot.send_message(partner, msg.text)
    except telebot.apihelper.ApiException:
        # Партнёр заблокировал бота — отключаем
        disconnect(uid)
        bot.send_message(uid, "🔴 Собеседник недоступен. Чат завершён.")


@bot.message_handler(content_types=["sticker"])
def relay_sticker(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_sticker(partner, msg.sticker.file_id)
        except Exception:
            pass
    else:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.")


@bot.message_handler(content_types=["photo"])
def relay_photo(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            best = msg.photo[-1].file_id  # наибольшее разрешение
            bot.send_photo(partner, best, caption=msg.caption)
        except Exception:
            pass
    else:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.")


@bot.message_handler(content_types=["video"])
def relay_video(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_video(partner, msg.video.file_id, caption=msg.caption)
        except Exception:
            pass
    else:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.")


@bot.message_handler(content_types=["voice"])
def relay_voice(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_voice(partner, msg.voice.file_id)
        except Exception:
            pass
    else:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.")


@bot.message_handler(content_types=["document"])
def relay_document(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_document(partner, msg.document.file_id, caption=msg.caption)
        except Exception:
            pass
    else:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.")


@bot.message_handler(content_types=["video_note"])
def relay_videonote(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_video_note(partner, msg.video_note.file_id)
        except Exception:
            pass
    else:
        bot.send_message(uid, "Нажми /start чтобы найти собеседника.")


# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Bot starting...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
