from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from config import webapp_url

router = Router()


TEXTS = {
    "ru": {
        "button": "🐝 Открыть пасеку",
        "welcome": "Добро пожаловать в систему управления пасекой!\n\n"
                   "Нажмите кнопку ниже, чтобы открыть приложение: ульи, матки, осмотры, мёд и отчёты.",
    },
    "tg": {
        "button": "🐝 Кушодани занбӯрхона",
        "welcome": "Хуш омадед ба системаи идоракунии занбӯрхона!\n\n"
                   "Барои кушодани барнома тугмаи поёнро пахш кунед: қуттиҳо, модарзанбӯрҳо, муоинаҳо, асал ва ҳисоботҳо.",
    },
}


def lang_of(message: Message) -> str:
    """Telegram language of the user: Tajik for tg, Russian otherwise."""
    code = (message.from_user.language_code if message.from_user else None) or ""
    return "tg" if code.lower().startswith("tg") else "ru"


def open_app_keyboard(lang: str = "ru") -> InlineKeyboardMarkup | None:
    url = webapp_url()
    if not url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=TEXTS[lang]["button"], web_app=WebAppInfo(url=url))]]
    )


@router.message(CommandStart())
async def start(message: Message, command: CommandObject) -> None:
    lang = lang_of(message)
    await message.answer(TEXTS[lang]["welcome"], reply_markup=open_app_keyboard(lang))
