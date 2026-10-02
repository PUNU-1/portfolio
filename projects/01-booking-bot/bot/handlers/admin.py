"""Команды администратора."""
from html import escape

from aiogram import Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import Message

from ..config import Business, Settings
from ..db import Database
from ..formatting import format_date, user_link

router = Router()


class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, settings: Settings) -> bool:
        return message.from_user is not None and message.from_user.id in settings.admin_ids


@router.message(Command("today"), IsAdmin())
async def cmd_today(message: Message, db: Database, business: Business) -> None:
    today = business.now().date()
    bookings = await db.bookings_on(today)
    if not bookings:
        await message.answer(f"На сегодня ({format_date(today)}) записей нет.")
        return

    lines = [f"<b>Записи на сегодня: {format_date(today)}</b> (всего {len(bookings)})", ""]
    for booking in bookings:
        lines.append(
            f"{booking.start_time}–{booking.end_time} · {escape(booking.service_name)} · {user_link(booking)}"
        )
    await message.answer("\n".join(lines))


@router.message(Command("today"))
async def cmd_today_denied(message: Message) -> None:
    await message.answer("Эта команда только для администратора.")
