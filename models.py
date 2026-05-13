from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.reply import main_kb

router = Router()

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Добро пожаловать в Anonymous Chat",
        reply_markup=main_kb()
    )
