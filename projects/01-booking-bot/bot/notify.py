"""Уведомления владельцу."""
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from .config import Settings

log = logging.getLogger(__name__)


async def notify_owner(bot: Bot, settings: Settings, text: str) -> None:
    """Отправляет владельцу сообщение. Ошибка отправки не должна ломать запись клиента."""
    try:
        await bot.send_message(settings.owner_id, text)
    except TelegramAPIError as error:
        log.warning(
            "Не удалось уведомить владельца (%s). Проверьте OWNER_ID и что владелец нажал /start у бота.",
            error,
        )
