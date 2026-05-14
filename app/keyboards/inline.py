from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.reports import REPORT_CATEGORIES


INTERESTS = {
    "games": "🎮 Игры",
    "music": "🎵 Музыка",
    "relations": "💕 Отношения",
    "it": "💻 IT",
    "films": "🎬 Фильмы",
    "flirt": "😈 Флирт",
}


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="🇺🇸 English", callback_data="lang:en"),
            ]
        ]
    )


def gender_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Любой", callback_data="pref_gender:any"),
                InlineKeyboardButton(text="Парень", callback_data="pref_gender:male"),
                InlineKeyboardButton(text="Девушка", callback_data="pref_gender:female"),
            ]
        ]
    )


def interests_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"interest:{key}")]
        for key, label in INTERESTS.items()
    ]
    rows.append([InlineKeyboardButton(text="Готово", callback_data="interest_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_chat_kb(partner_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍", callback_data=f"rate:{partner_id}:like"),
                InlineKeyboardButton(text="👎", callback_data=f"rate:{partner_id}:dislike"),
            ],
            [InlineKeyboardButton(text="🚨 Пожаловаться", callback_data=f"report_menu:{partner_id}")],
        ]
    )


def report_kb(partner_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"report:{partner_id}:{key}")]
        for key, label in REPORT_CATEGORIES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
