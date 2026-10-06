from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import WEBAPP_URL

router = Router()


def open_app_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🐝 Открыть пасеку", web_app=WebAppInfo(url=WEBAPP_URL))]]
    )


@router.message(CommandStart())
async def start(message: Message, command: CommandObject) -> None:
    await message.answer(
        "Добро пожаловать в систему управления пасекой!\n\n"
        "Нажмите кнопку ниже, чтобы открыть приложение: ульи, матки, осмотры, мёд и отчёты.",
        reply_markup=open_app_keyboard(),
    )
