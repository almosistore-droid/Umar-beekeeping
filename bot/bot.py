"""Telegram bot: entry point to the Mini App, login confirmation for the phone app, reminders (stage 8)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from config import BOT_TOKEN, SET_MENU_BUTTON, webapp_url
from handlers import login, start
import reminders

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(login.router)  # before start: /start login_<code> is a login confirmation
    dp.include_router(start.router)

    await bot.set_my_commands([BotCommand(command="start", description="Открыть пасеку")])
    await bot.set_my_commands([BotCommand(command="start", description="Кушодани занбӯрхона")], language_code="tg")
    # Persistent "Пасека" button next to the input field opens the Mini App (dev: the tunnel sets it)
    url = webapp_url()
    if SET_MENU_BUTTON and url:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Пасека", web_app=WebAppInfo(url=url)))

    reminder_loop = asyncio.create_task(reminders.run_forever())  # stage 8: Telegram reminders
    try:
        await dp.start_polling(bot)
    finally:
        reminder_loop.cancel()


if __name__ == "__main__":
    asyncio.run(main())
