"""Запасные обработчики: подключаются последними и ловят всё, что не подошло остальным."""
from aiogram import Router
from aiogram.types import CallbackQuery, Message

router = Router()


@router.callback_query()
async def stale_button(cb: CallbackQuery) -> None:
    # Бывает, когда бот перезапускали, а клиент нажал кнопку из старого сообщения
    await cb.answer("Эта кнопка устарела. Нажмите /start", show_alert=True)


@router.message()
async def unknown_message(message: Message) -> None:
    await message.answer("Не понял вас. Чтобы записаться, нажмите /book. Все команды: /start")
