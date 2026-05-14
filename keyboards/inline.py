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

PROFILE_EMOJIS = {
    "⭐": "⭐ Звезда",
    "🔥": "🔥 Огонь",
    "😎": "😎 Стильно",
    "🎭": "🎭 Аноним",
    "🌙": "🌙 Ночной",
    "💬": "💬 Общение",
}

PROFILE_THEMES = {
    "default": "Default",
    "midnight": "Midnight",
    "sunset": "Sunset",
    "neon": "Neon",
}


def _selected(text: str, active: bool) -> str:
    return f"• {text}" if active else text


def language_kb(selected: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_selected("🇷🇺 Русский", selected == "ru"), callback_data="lang:ru"),
                InlineKeyboardButton(text=_selected("🇺🇸 English", selected == "en"), callback_data="lang:en"),
            ]
        ]
    )


def gender_filter_kb(selected: str = "any") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_selected("Любой", selected == "any"), callback_data="pref_gender:any"),
                InlineKeyboardButton(text=_selected("Парень", selected == "male"), callback_data="pref_gender:male"),
                InlineKeyboardButton(text=_selected("Девушка", selected == "female"), callback_data="pref_gender:female"),
            ]
        ]
    )


def profile_gender_kb(selected: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=_selected("Не указан", selected == ""), callback_data="gender:"),
                InlineKeyboardButton(text=_selected("Парень", selected == "male"), callback_data="gender:male"),
                InlineKeyboardButton(text=_selected("Девушка", selected == "female"), callback_data="gender:female"),
            ]
        ]
    )


def interests_kb(selected: set[str] | None = None) -> InlineKeyboardMarkup:
    selected = selected or set()
    rows = [
        [InlineKeyboardButton(text=_selected(label, key in selected), callback_data=f"interest:{key}")]
        for key, label in INTERESTS.items()
    ]
    rows.append([InlineKeyboardButton(text="Готово", callback_data="interest_done")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Пол", callback_data="settings:gender"),
                InlineKeyboardButton(text="Возраст", callback_data="settings:age"),
            ],
            [
                InlineKeyboardButton(text="Статус", callback_data="settings:status"),
                InlineKeyboardButton(text="Emoji", callback_data="settings:emoji"),
            ],
            [
                InlineKeyboardButton(text="Theme", callback_data="settings:theme"),
                InlineKeyboardButton(text="Очистить статус", callback_data="settings:status_clear"),
            ],
        ]
    )


def emoji_kb(selected: str = "⭐") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=_selected(label, emoji == selected), callback_data=f"emoji:{emoji}")]
        for emoji, label in PROFILE_EMOJIS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def theme_kb(selected: str = "default") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=_selected(label, theme == selected), callback_data=f"theme:{theme}")]
        for theme, label in PROFILE_THEMES.items()
    ]
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
