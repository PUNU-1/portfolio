"""Сборка диспетчера. Вынесена из main.py, чтобы тесты могли собрать бота без запуска."""
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .config import Business, Settings
from .db import Database
from .handlers import routers


def build_dispatcher(settings: Settings, business: Business, db: Database) -> Dispatcher:
    # Всё, что передано в Dispatcher(...) как именованный аргумент,
    # становится доступно обработчикам по имени: async def handler(message, db, business)
    dp = Dispatcher(storage=MemoryStorage(), settings=settings, business=business, db=db)
    for router in routers:
        dp.include_router(router)
    return dp
