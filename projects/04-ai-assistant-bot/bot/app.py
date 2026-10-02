"""Сборка диспетчера. Вынесена из main.py, чтобы тесты могли собрать бота без запуска."""
from aiogram import Dispatcher

from .assistant import Assistant
from .config import Settings
from .handlers import router


def build_dispatcher(settings: Settings, assistant: Assistant) -> Dispatcher:
    # Именованные аргументы Dispatcher(...) доступны обработчикам по имени параметра
    dp = Dispatcher(settings=settings, assistant=assistant)
    dp.include_router(router)
    return dp
