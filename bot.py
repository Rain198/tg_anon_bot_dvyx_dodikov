"""
╔══════════════════════════════════════════════════════════╗
║          ANONYMOUS CHAT BOT — ПОЛНАЯ ВЕРСИЯ              ║
╠══════════════════════════════════════════════════════════╣
║  Функции:                                                ║
║  • Профили (пол, возраст) — обязательны перед чатом      ║
║  • Поиск по полу или любой                               ║
║  • Репорт фото/видео на 18+ контент                      ║
║  • Панель модератора (/mod_panel)                         ║
║  • Реакции после чата (👍 👎 🤷 💫 🔥)                  ║
║  • Просмотр профиля /profile                             ║
╠══════════════════════════════════════════════════════════╣
║  Зависимости:  pip install pyTelegramBotAPI              ║
║  Запуск:                                                 ║
║    BOT_TOKEN=... ADMIN_IDS=123,456 python bot.py         ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import logging
import time
from dataclasses import dataclass, field
from typing import Optional
import telebot
from telebot import types

# ══════════════════════════════════════════════════════════════════
#  КОНФИГ
# ══════════════════════════════════════════════════════════════════
BOT_TOKEN   = os.getenv("BOT_TOKEN", "8847730026:AAE2w2AByxiSRXCPSssP5QsT5QsdBgapHzk")
_raw_admins = os.getenv("ADMIN_IDS", "5428663703,8484221382")   # "123456,789012"
ADMIN_IDS: set[int] = {int(x) for x in _raw_admins.split(",") if x.strip().isdigit()}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ══════════════════════════════════════════════════════════════════
#  СТРУКТУРЫ ДАННЫХ
# ══════════════════════════════════════════════════════════════════

REACTIONS = ["👍", "👎", "🤷", "💫", "🔥"]
# 👍 Лайк | 👎 Дизлайк | 🤷 50/50 | 💫 На одной волне | 🔥 Огонь


@dataclass
class Profile:
    uid:          int
    gender:       str  = ""     # "male" | "female" | "other"
    age:          int  = 0
    reactions:    dict = field(default_factory=lambda: {r: 0 for r in REACTIONS})
    chats_count:  int  = 0
    banned:       bool = False
    registered:   bool = False


@dataclass
class Report:
    report_id:   int
    reporter_id: int
    reported_id: int
    media_type:  str    # "photo" | "video"
    file_id:     str
    ts:          float = field(default_factory=time.time)
    resolved:    bool  = False
    action:      str   = ""   # "banned" | "cleared"


# ══════════════════════════════════════════════════════════════════
#  ХРАНИЛИЩЕ
# ══════════════════════════════════════════════════════════════════
profiles:  dict[int, Profile]         = {}
pairs:     dict[int, int]             = {}   # uid -> partner_uid
waiting:   list[tuple[int, str]]      = []   # [(uid, gender_pref)]
reports:   list[Report]               = []
_report_seq: int                      = 0

reg_state:        dict[int, str]  = {}  # uid -> "await_gender" | "await_age"
pending_reaction: dict[int, int]  = {}  # uid -> partner_uid
last_media:       dict[int, dict] = {}  # uid -> {type, file_id, partner}


# ══════════════════════════════════════════════════════════════════
#  КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════════════

def kb_main() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔍 Найти собеседника", "⏭ Следующий")
    kb.row("🛑 Стоп",             "👤 Профиль")
    kb.row("❓ Помощь")
    return kb


def kb_gender_pref() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("👦 Парень",  callback_data="find:male"),
        types.InlineKeyboardButton("👧 Девушка", callback_data="find:female"),
        types.InlineKeyboardButton("🎲 Любой",   callback_data="find:any"),
    )
    return kb


def kb_reg_gender() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("👦 Парень",  callback_data="reg_gender:male"),
        types.InlineKeyboardButton("👧 Девушка", callback_data="reg_gender:female"),
        types.InlineKeyboardButton("🌈 Другое",  callback_data="reg_gender:other"),
    )
    return kb


def kb_reactions() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(*[types.InlineKeyboardButton(e, callback_data=f"react:{e}") for e in REACTIONS])
    return kb


def kb_report(media_type: str, file_id: str) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🚨 Репорт 18+",
        callback_data=f"report:{media_type}:{file_id}"
    ))
    return kb


def kb_mod_action(report_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("🔨 Забанить", callback_data=f"mod_ban:{report_id}"),
        types.InlineKeyboardButton("✅ Очистить",  callback_data=f"mod_clear:{report_id}"),
    )
    return kb


# ══════════════════════════════════════════════════════════════════
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ══════════════════════════════════════════════════════════════════

def get_profile(uid: int) -> Profile:
    if uid not in profiles:
        profiles[uid] = Profile(uid=uid)
    return profiles[uid]


def gender_label(g: str) -> str:
    return {"male": "👦 Парень", "female": "👧 Девушка", "other": "🌈 Другое"}.get(g, "❓")


def in_chat(uid: int) -> bool:
    return uid in pairs


def in_queue(uid: int) -> bool:
    return any(u == uid for u, _ in waiting)


def remove_from_queue(uid: int) -> None:
    global waiting
    waiting = [(u, p) for u, p in waiting if u != uid]


def disconnect(uid: int, notify_partner: bool = True) -> Optional[int]:
    partner = pairs.pop(uid, None)
    if partner:
        pairs.pop(partner, None)
        if notify_partner:
            try:
                bot.send_message(
                    partner,
                    "🔴 Собеседник покинул чат.\n\n"
                    "Нажми «🔍 Найти собеседника» чтобы начать новый.",
                    reply_markup=kb_main()
                )
            except Exception:
                pass
    return partner


def offer_reaction(uid: int, partner_uid: int) -> None:
    pending_reaction[uid] = partner_uid
    try:
        bot.send_message(
            uid,
            "💬 Чат завершён! Как прошло общение?\nОставь реакцию собеседнику:",
            reply_markup=kb_reactions()
        )
    except Exception:
        pass


def try_match() -> None:
    i = 0
    while i < len(waiting):
        uid1, pref1 = waiting[i]
        p1 = get_profile(uid1)
        matched = False
        for j in range(i + 1, len(waiting)):
            uid2, pref2 = waiting[j]
            p2 = get_profile(uid2)
            ok1 = (pref1 == "any" or pref1 == p2.gender)
            ok2 = (pref2 == "any" or pref2 == p1.gender)
            if ok1 and ok2:
                waiting.pop(j)
                waiting.pop(i)
                pairs[uid1] = uid2
                pairs[uid2] = uid1
                p1.chats_count += 1
                p2.chats_count += 1
                conn_msg = (
                    "✅ Собеседник найден! Общайтесь анонимно.\n\n"
                    "Если получишь фото/видео 18+ — нажми кнопку «🚨 Репорт 18+» под ним.\n\n"
                    "/stop — завершить  |  /next — новый собеседник"
                )
                try:
                    bot.send_message(uid1, conn_msg, reply_markup=kb_main())
                    bot.send_message(uid2, conn_msg, reply_markup=kb_main())
                    log.info("Matched %s <-> %s", uid1, uid2)
                except Exception as e:
                    log.warning("Match error: %s", e)
                matched = True
                break
        if not matched:
            i += 1


def add_report(reporter: int, reported: int, mtype: str, fid: str) -> Report:
    global _report_seq
    _report_seq += 1
    r = Report(
        report_id=_report_seq,
        reporter_id=reporter,
        reported_id=reported,
        media_type=mtype,
        file_id=fid,
    )
    reports.append(r)
    return r


def notify_admins_report(r: Report) -> None:
    p = get_profile(r.reported_id)
    reports_on_user = sum(1 for x in reports if x.reported_id == r.reported_id)
    caption = (
        f"🚨 РЕПОРТ #{r.report_id}\n"
        f"Тип медиа: {r.media_type}\n"
        f"Профиль: {gender_label(p.gender)}, {p.age} лет\n"
        f"Всего репортов на пользователя: {reports_on_user}"
    )
    for admin_id in ADMIN_IDS:
        try:
            if r.media_type == "photo":
                bot.send_photo(admin_id, r.file_id, caption=caption,
                               reply_markup=kb_mod_action(r.report_id))
            else:
                bot.send_video(admin_id, r.file_id, caption=caption,
                               reply_markup=kb_mod_action(r.report_id))
        except Exception as e:
            log.warning("Admin notify error: %s", e)


# ══════════════════════════════════════════════════════════════════
#  РЕГИСТРАЦИЯ
# ══════════════════════════════════════════════════════════════════

def start_registration(uid: int) -> None:
    reg_state[uid] = "await_gender"
    bot.send_message(
        uid,
        "👋 Добро пожаловать!\n\n"
        "Прежде чем начать, создай мини-профиль.\n\n"
        "1️⃣ Укажи свой пол:",
        reply_markup=kb_reg_gender()
    )


# ══════════════════════════════════════════════════════════════════
#  КОМАНДЫ
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(msg: types.Message) -> None:
    uid = msg.from_user.id
    if get_profile(uid).banned:
        bot.send_message(uid, "🚫 Вы заблокированы за нарушение правил.")
        return
    if not get_profile(uid).registered:
        start_registration(uid)
        return
    if in_chat(uid):
        bot.send_message(uid, "Ты уже в чате. /stop чтобы выйти.", reply_markup=kb_main())
        return
    bot.send_message(uid, "Кого ищешь?", reply_markup=kb_gender_pref())


@bot.message_handler(commands=["stop"])
def cmd_stop(msg: types.Message) -> None:
    uid = msg.from_user.id
    if in_chat(uid):
        partner = disconnect(uid)
        if partner:
            offer_reaction(uid, partner)
            offer_reaction(partner, uid)
        else:
            bot.send_message(uid, "🔴 Чат завершён.", reply_markup=kb_main())
        return
    if in_queue(uid):
        remove_from_queue(uid)
        bot.send_message(uid, "❌ Поиск отменён.", reply_markup=kb_main())
        return
    bot.send_message(uid, "Ты не в чате.", reply_markup=kb_main())


@bot.message_handler(commands=["next"])
def cmd_next(msg: types.Message) -> None:
    uid = msg.from_user.id
    if get_profile(uid).banned:
        bot.send_message(uid, "🚫 Вы заблокированы.")
        return
    if not get_profile(uid).registered:
        start_registration(uid)
        return
    if in_chat(uid):
        partner = disconnect(uid)
        if partner:
            offer_reaction(uid, partner)
            offer_reaction(partner, uid)
    remove_from_queue(uid)
    bot.send_message(uid, "🔄 Кого ищешь?", reply_markup=kb_gender_pref())


@bot.message_handler(commands=["profile"])
def cmd_profile(msg: types.Message) -> None:
    uid = msg.from_user.id
    p = get_profile(uid)
    if not p.registered:
        bot.send_message(uid, "Сначала пройди регистрацию /start")
        return
    reacts_str = "  ".join(f"{e} {p.reactions[e]}" for e in REACTIONS)
    text = (
        f"👤 Твой профиль\n\n"
        f"Пол: {gender_label(p.gender)}\n"
        f"Возраст: {p.age}\n"
        f"Чатов: {p.chats_count}\n\n"
        f"Реакции от собеседников:\n{reacts_str}"
    )
    bot.send_message(uid, text, reply_markup=kb_main())


@bot.message_handler(commands=["help"])
def cmd_help(msg: types.Message) -> None:
    text = (
        "Команды:\n"
        "/start   — найти собеседника\n"
        "/stop    — завершить чат\n"
        "/next    — новый собеседник\n"
        "/profile — мой профиль\n"
        "/help    — помощь\n\n"
        "Реакции после чата:\n"
        "👍 Лайк  👎 Дизлайк  🤷 50/50\n"
        "💫 На одной волне  🔥 Огонь\n\n"
        "Репорт 18+:\n"
        "Под каждым фото/видео в чате есть кнопка «🚨 Репорт 18+».\n"
        "Нажми если контент неприемлемый — модераторы рассмотрят."
    )
    bot.send_message(msg.from_user.id, text, reply_markup=kb_main())


@bot.message_handler(commands=["mod_panel"])
def cmd_mod_panel(msg: types.Message) -> None:
    uid = msg.from_user.id
    if uid not in ADMIN_IDS:
        bot.send_message(uid, "⛔ Нет доступа.")
        return
    open_r  = [r for r in reports if not r.resolved]
    bans    = sum(1 for p in profiles.values() if p.banned)
    text = (
        f"Панель модератора\n\n"
        f"Всего репортов: {len(reports)}\n"
        f"Открытых: {len(open_r)}\n"
        f"Забанено: {bans}\n\n"
    )
    if open_r:
        text += "Последние открытые:\n"
        for r in open_r[-5:]:
            p = get_profile(r.reported_id)
            text += f"  #{r.report_id} {r.media_type} | {gender_label(p.gender)} {p.age}л\n"
    else:
        text += "Открытых репортов нет."
    bot.send_message(uid, text)


# ══════════════════════════════════════════════════════════════════
#  КНОПКИ ГЛАВНОГО МЕНЮ
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text == "🔍 Найти собеседника")
def btn_find(msg: types.Message) -> None:
    cmd_start(msg)

@bot.message_handler(func=lambda m: m.text == "⏭ Следующий")
def btn_next(msg: types.Message) -> None:
    cmd_next(msg)

@bot.message_handler(func=lambda m: m.text == "🛑 Стоп")
def btn_stop(msg: types.Message) -> None:
    cmd_stop(msg)

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def btn_profile(msg: types.Message) -> None:
    cmd_profile(msg)

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def btn_help(msg: types.Message) -> None:
    cmd_help(msg)


# ══════════════════════════════════════════════════════════════════
#  CALLBACK HANDLERS
# ══════════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: c.data.startswith("reg_gender:"))
def cb_reg_gender(call: types.CallbackQuery) -> None:
    uid    = call.from_user.id
    gender = call.data.split(":")[1]
    get_profile(uid).gender = gender
    reg_state[uid] = "await_age"
    bot.answer_callback_query(call.id)
    bot.edit_message_text(
        f"Пол: {gender_label(gender)} ✅\n\n"
        f"2️⃣ Теперь введи свой возраст (13–99):",
        chat_id=uid,
        message_id=call.message.message_id
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("find:"))
def cb_find(call: types.CallbackQuery) -> None:
    uid  = call.from_user.id
    pref = call.data.split(":")[1]
    bot.answer_callback_query(call.id)

    if get_profile(uid).banned:
        bot.send_message(uid, "🚫 Вы заблокированы.")
        return
    if in_chat(uid):
        bot.send_message(uid, "Ты уже в чате. /stop чтобы выйти.")
        return
    if in_queue(uid):
        bot.send_message(uid, "⏳ Уже в поиске...")
        return

    waiting.append((uid, pref))
    label = {"male": "парня 👦", "female": "девушку 👧", "any": "любого 🎲"}.get(pref, "")
    bot.send_message(uid, f"🔍 Ищем {label}...", reply_markup=kb_main())
    try_match()


@bot.callback_query_handler(func=lambda c: c.data.startswith("react:"))
def cb_reaction(call: types.CallbackQuery) -> None:
    uid   = call.from_user.id
    emoji = call.data.split(":")[1]

    if uid not in pending_reaction:
        bot.answer_callback_query(call.id, "Реакция уже отправлена.")
        return

    partner_uid = pending_reaction.pop(uid)
    p = get_profile(partner_uid)
    if emoji in p.reactions:
        p.reactions[emoji] += 1

    bot.answer_callback_query(call.id, f"Реакция {emoji} отправлена!")
    try:
        bot.edit_message_reply_markup(chat_id=uid, message_id=call.message.message_id, reply_markup=None)
        bot.send_message(uid, f"Ты поставил {emoji}", reply_markup=kb_main())
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("report:"))
def cb_report(call: types.CallbackQuery) -> None:
    uid   = call.from_user.id
    parts = call.data.split(":", 2)
    if len(parts) < 3:
        bot.answer_callback_query(call.id, "Ошибка данных.")
        return
    mtype = parts[1]
    fid   = parts[2]

    # Найти отправителя медиа через last_media
    lm = last_media.get(uid)
    reported_uid = lm.get("partner") if (lm and lm.get("file_id") == fid) else None

    if reported_uid is None:
        bot.answer_callback_query(call.id, "Не удалось определить отправителя. Возможно, чат завершён.")
        return

    r = add_report(uid, reported_uid, mtype, fid)
    bot.answer_callback_query(call.id, "🚨 Репорт принят! Спасибо.")
    bot.send_message(uid, "Репорт передан модераторам. Спасибо за помощь!")
    notify_admins_report(r)
    log.info("Report #%s: user %s reported %s (%s)", r.report_id, uid, reported_uid, mtype)


@bot.callback_query_handler(func=lambda c: c.data.startswith("mod_ban:"))
def cb_mod_ban(call: types.CallbackQuery) -> None:
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return
    report_id = int(call.data.split(":")[1])
    r = next((x for x in reports if x.report_id == report_id), None)
    if not r:
        bot.answer_callback_query(call.id, "Репорт не найден.")
        return
    if r.resolved:
        bot.answer_callback_query(call.id, "Уже обработан.")
        return

    r.resolved = True
    r.action   = "banned"
    get_profile(r.reported_id).banned = True

    if in_chat(r.reported_id):
        disconnect(r.reported_id)

    try:
        bot.send_message(r.reported_id, "🚫 Вы заблокированы за отправку 18+ контента.")
    except Exception:
        pass

    bot.answer_callback_query(call.id, "Пользователь забанен.")
    try:
        new_caption = f"РЕШЕНО — Забанен\n\n{call.message.caption or ''}"
        bot.edit_message_caption(caption=new_caption,
                                 chat_id=call.message.chat.id,
                                 message_id=call.message.message_id,
                                 reply_markup=None)
    except Exception:
        pass
    log.info("Admin %s banned user %s (report #%s)", call.from_user.id, r.reported_id, report_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("mod_clear:"))
def cb_mod_clear(call: types.CallbackQuery) -> None:
    if call.from_user.id not in ADMIN_IDS:
        bot.answer_callback_query(call.id, "⛔ Нет доступа.")
        return
    report_id = int(call.data.split(":")[1])
    r = next((x for x in reports if x.report_id == report_id), None)
    if not r:
        bot.answer_callback_query(call.id, "Репорт не найден.")
        return
    if r.resolved:
        bot.answer_callback_query(call.id, "Уже обработан.")
        return

    r.resolved = True
    r.action   = "cleared"

    bot.answer_callback_query(call.id, "Репорт закрыт — нарушений нет.")
    try:
        new_caption = f"РЕШЕНО — Нарушений нет\n\n{call.message.caption or ''}"
        bot.edit_message_caption(caption=new_caption,
                                 chat_id=call.message.chat.id,
                                 message_id=call.message.message_id,
                                 reply_markup=None)
    except Exception:
        pass
    log.info("Admin %s cleared report #%s", call.from_user.id, report_id)


# ══════════════════════════════════════════════════════════════════
#  ВВОД ВОЗРАСТА (в процессе регистрации)
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(func=lambda m: reg_state.get(m.from_user.id) == "await_age")
def handle_age_input(msg: types.Message) -> None:
    uid  = msg.from_user.id
    text = (msg.text or "").strip()
    if not text.isdigit() or not (13 <= int(text) <= 99):
        bot.send_message(uid, "Введи корректный возраст от 13 до 99:")
        return
    p = get_profile(uid)
    p.age = int(text)
    p.registered = True
    del reg_state[uid]
    bot.send_message(
        uid,
        f"Профиль создан!\n\n"
        f"Пол: {gender_label(p.gender)}\n"
        f"Возраст: {p.age}\n\n"
        f"Нажми «Найти собеседника»!",
        reply_markup=kb_main()
    )


# ══════════════════════════════════════════════════════════════════
#  ПЕРЕСЫЛКА СООБЩЕНИЙ
# ══════════════════════════════════════════════════════════════════

@bot.message_handler(content_types=["text"])
def relay_text(msg: types.Message) -> None:
    uid = msg.from_user.id
    if reg_state.get(uid):
        return  # обрабатывается выше
    partner = pairs.get(uid)
    if partner is None:
        bot.send_message(uid, "Нажми «🔍 Найти собеседника».", reply_markup=kb_main())
        return
    try:
        bot.send_message(partner, msg.text)
    except Exception:
        disconnect(uid)
        bot.send_message(uid, "Собеседник недоступен. Чат завершён.", reply_markup=kb_main())


@bot.message_handler(content_types=["photo"])
def relay_photo(msg: types.Message) -> None:
    uid     = msg.from_user.id
    partner = pairs.get(uid)
    if not partner:
        bot.send_message(uid, "Нажми «🔍 Найти собеседника».")
        return
    fid = msg.photo[-1].file_id
    last_media[partner] = {"type": "photo", "file_id": fid, "partner": uid}
    try:
        bot.send_photo(partner, fid, caption=msg.caption or "",
                       reply_markup=kb_report("photo", fid))
    except Exception:
        pass


@bot.message_handler(content_types=["video"])
def relay_video(msg: types.Message) -> None:
    uid     = msg.from_user.id
    partner = pairs.get(uid)
    if not partner:
        bot.send_message(uid, "Нажми «🔍 Найти собеседника».")
        return
    fid = msg.video.file_id
    last_media[partner] = {"type": "video", "file_id": fid, "partner": uid}
    try:
        bot.send_video(partner, fid, caption=msg.caption or "",
                       reply_markup=kb_report("video", fid))
    except Exception:
        pass


@bot.message_handler(content_types=["sticker"])
def relay_sticker(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_sticker(partner, msg.sticker.file_id)
        except Exception:
            pass


@bot.message_handler(content_types=["voice"])
def relay_voice(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_voice(partner, msg.voice.file_id)
        except Exception:
            pass


@bot.message_handler(content_types=["video_note"])
def relay_video_note(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_video_note(partner, msg.video_note.file_id)
        except Exception:
            pass


@bot.message_handler(content_types=["document"])
def relay_document(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_document(partner, msg.document.file_id, caption=msg.caption)
        except Exception:
            pass


@bot.message_handler(content_types=["audio"])
def relay_audio(msg: types.Message) -> None:
    uid = msg.from_user.id
    partner = pairs.get(uid)
    if partner:
        try:
            bot.send_audio(partner, msg.audio.file_id, caption=msg.caption)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if not ADMIN_IDS:
        log.warning("ADMIN_IDS не задан! Установи переменную окружения: ADMIN_IDS=твой_telegram_id")
    log.info("Bot starting... Admins: %s", ADMIN_IDS)
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
