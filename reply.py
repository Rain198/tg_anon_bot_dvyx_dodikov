from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message(lambda m: m.text == "👤 Профиль")
async def profile(message: Message):
    text = (
        "👤 Профиль\n\n"
        "Репутация: 100\n"
        "Premium: Нет"
    )

    await message.answer(text)
