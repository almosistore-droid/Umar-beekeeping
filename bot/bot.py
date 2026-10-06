"""Telegram bot: entry point to the Mini App (notifications are added in stage 8)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

from config import BOT_TOKEN, WEBAPP_URL
from handlers import start

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(start.router)

    await bot.set_my_commands([BotCommand(command="start", description="Открыть пасеку")])
    # Persistent "Пасека" button next to the input field opens the Mini App
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Пасека", web_app=WebAppInfo(url=WEBAPP_URL)))

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
