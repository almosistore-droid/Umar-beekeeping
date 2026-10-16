"""Login confirmation for the app installed on the phone (outside Telegram).

The app opens t.me/<bot>?start=login_<code>; the user confirms here. The backend trusts this because the
Telegram user in an update comes from Telegram's servers, and the request is signed with the bot token.
"""
from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import backend_client

router = Router()
CODE_RE = r"^login_[A-Za-z0-9_-]{16,58}$"

TEXTS = {
    "ru": {
        "ask": "Войти в приложение Fayzi Umar на телефоне?\n\n"
               "Нажмите «Войти», только если вы сами только что нажали «Войти через Telegram» в приложении. "
               "Если нет — нажмите «Отмена».",
        "yes": "✅ Войти",
        "no": "Отмена",
        "done": "Готово, {name}! Вернитесь в приложение — вход выполнен.",
        "cancelled": "Вход отменён.",
        "fail": "Не удалось войти. Попробуйте ещё раз из приложения.",
    },
    "tg": {
        "ask": "Ба барномаи Fayzi Umar дар телефон ворид мешавед?\n\n"
               "«Ворид шудан»-ро танҳо он вақт пахш кунед, ки худатон ҳоло дар барнома "
               "«Ворид шудан тавассути Telegram»-ро пахш карда бошед. Агар не — «Бекор кардан»-ро пахш кунед.",
        "yes": "✅ Ворид шудан",
        "no": "Бекор кардан",
        "done": "Тайёр, {name}! Ба барнома баргардед — шумо ворид шудед.",
        "cancelled": "Воридшавӣ бекор карда шуд.",
        "fail": "Ворид шудан муяссар нашуд. Аз барнома боз кӯшиш кунед.",
    },
}


def lang_from(code: str | None) -> str:
    return "tg" if (code or "").lower().startswith("tg") else "ru"


@router.message(CommandStart(deep_link=True, magic=F.args.regexp(CODE_RE)))
async def ask(message: Message, command: CommandObject) -> None:
    code = command.args.removeprefix("login_")
    t = TEXTS[lang_from(message.from_user.language_code if message.from_user else None)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t["yes"], callback_data=f"lok:{code}"),
        InlineKeyboardButton(text=t["no"], callback_data=f"lno:{code}"),
    ]])
    await message.answer(t["ask"], reply_markup=keyboard)


@router.callback_query(F.data.regexp(r"^l(ok|no):[A-Za-z0-9_-]{16,58}$"))
async def answer(callback: CallbackQuery) -> None:
    action, code = callback.data.split(":", 1)
    user = callback.from_user
    lang = lang_from(user.language_code)
    t = TEXTS[lang]
    if action == "lok":
        status, body = await backend_client.post("/api/auth/login-codes/confirm", {
            "code": code,
            "user": {"id": user.id, "first_name": user.first_name, "last_name": user.last_name,
                     "username": user.username, "language_code": user.language_code},
        }, lang)
        if status == 200:
            text = t["done"].format(name=body.get("display_name") or user.first_name or "")
        else:
            text = body.get("detail") if isinstance(body.get("detail"), str) else t["fail"]
    else:
        await backend_client.post("/api/auth/login-codes/deny", {"code": code}, lang)
        text = t["cancelled"]
    if callback.message:
        await callback.message.edit_text(text)  # also removes the buttons: a code is used once
    await callback.answer()
