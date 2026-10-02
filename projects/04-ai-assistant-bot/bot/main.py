"""Точка входа: python -m bot.main"""
import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.types import BotCommand

from .app import build_dispatcher
from .assistant import Assistant
from .config import load_settings
from .knowledge import KnowledgeBase
from .llm import create_llm
from .storage import Storage

log = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="О боте и лимитах"),
    BotCommand(command="reset", description="Забыть наш разговор"),
    BotCommand(command="operator", description="Связаться с оператором"),
]


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    settings = load_settings()
    kb = KnowledgeBase.from_file(settings.knowledge_file)
    storage = Storage(settings.db_path)
    await storage.init()
    assistant = Assistant(settings, kb, create_llm(settings), storage)

    log.info("База знаний: %d блоков. Модель: %s", len(kb.chunks), "mock (без ИИ)" if settings.llm_provider == "mock" else settings.llm_model)

    bot = Bot(settings.bot_token)
    dp = build_dispatcher(settings, assistant)
    try:
        me = await bot.get_me()
        await bot.set_my_commands(COMMANDS)
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
