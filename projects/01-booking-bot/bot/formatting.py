"""Тексты и форматирование: даты по-русски, строки записей, ссылки на клиентов."""
from datetime import date
from html import escape

from aiogram.types import User

from .db import Booking

WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
MONTHS = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def format_date(day: date) -> str:
    """2025-01-31 -> 'пт, 31 января'."""
    return f"{WEEKDAYS[day.weekday()]}, {day.day} {MONTHS[day.month - 1]}"


def format_booking(booking: Booking) -> str:
    return (
        f"{format_date(booking.on_date)}, {booking.start_time}–{booking.end_time}\n"
        f"{escape(booking.service_name)} · {booking.price} ₽"
    )


def user_display_name(user: User) -> str:
    """Имя для записи в БД: 'Иван (@ivan)'."""
    return f"{user.full_name} (@{user.username})" if user.username else user.full_name


def user_link(booking: Booking) -> str:
    """Кликабельное имя клиента для владельца: открывает чат с ним."""
    return f'<a href="tg://user?id={booking.user_id}">{escape(booking.user_name)}</a>'
