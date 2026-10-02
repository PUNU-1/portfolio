"""Точка входа: python -m bot.main"""
import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramUnauthorizedError
from aiogram.types import BotCommand, BotCommandScopeChat

from .app import build_dispatcher
from .config import load_business, load_settings
from .db import Database

log = logging.getLogger(__name__)

USER_COMMANDS = [
    BotCommand(command="book", description="Записаться"),
    BotCommand(command="my_bookings", description="Мои записи"),
    BotCommand(command="cancel", description="Отменить"),
]
ADMIN_COMMANDS = USER_COMMANDS + [BotCommand(command="today", description="Записи на сегодня")]


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    business = load_business()
    db = Database(settings.db_path)
    await db.init()

    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = build_dispatcher(settings, business, db)

    try:
        me = await bot.get_me()
        await bot.set_my_commands(USER_COMMANDS)
        for admin_id in settings.admin_ids:
            try:
                await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
            except TelegramAPIError:
                log.warning("Не удалось выставить команды админу %s: он ещё не нажимал /start у бота", admin_id)

        log.info("Бот @%s запущен. Остановить: Ctrl+C", me.username)
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        raise SystemExit("Telegram не принял токен. Проверьте BOT_TOKEN в файле .env.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
