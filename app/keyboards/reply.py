from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Найти"), KeyboardButton(text="⏭ Следующий")],
            [KeyboardButton(text="🛑 Стоп"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="⚙️ Настройки"), KeyboardButton(text="👑 Premium")],
        ],
        resize_keyboard=True,
    )


def profile_setup_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🔍 Найти"), KeyboardButton(text="👑 Premium")],
        ],
        resize_keyboard=True,
    )
