from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.database.session import async_session
from app.keyboards.inline import language_kb
from app.keyboards.reply import main_kb
from app.services.captcha import create_captcha, verify_captcha
from app.services.users import get_or_create_user


router = Router()
captcha_waiting: set[int] = set()


@router.message(CommandStart())
async def start(message: Message) -> None:
    if not message.from_user:
        return

    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id)

    if user.banned:
        await message.answer("🚫 Вы заблокированы.")
        return

    if message.from_user.id not in captcha_waiting:
        captcha_waiting.add(message.from_user.id)
        await message.answer(create_captcha(message.from_user.id))
        return

    await message.answer("Добро пожаловать в анонимный чат.", reply_markup=main_kb())


@router.message(lambda message: message.from_user and message.from_user.id in captcha_waiting)
async def captcha_answer(message: Message) -> None:
    if not message.from_user:
        return

    if not verify_captcha(message.from_user.id, message.text):
        await message.answer("❌ Неверно. Попробуйте еще раз.")
        return

    captcha_waiting.discard(message.from_user.id)
    await message.answer("✅ Проверка пройдена.", reply_markup=main_kb())
    await message.answer("Выберите язык поиска:", reply_markup=language_kb())
