"""Inline-клавиатуры. Формат callback_data: «действие:значение»."""
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .config import Business
from .db import Booking
from .formatting import format_date


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Записаться", callback_data="menu:book")
    builder.button(text="Мои записи", callback_data="menu:my")
    builder.adjust(1)
    return builder.as_markup()


def services_kb(business: Business) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in business.services:
        builder.button(
            text=f"{service.name} · {service.price} ₽ · {service.duration_min} мин",
            callback_data=f"svc:{service.id}",
        )
    builder.button(text="Отмена", callback_data="flow:cancel")
    builder.adjust(1)
    return builder.as_markup()


def dates_kb(days: list[date]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for day in days:
        builder.button(text=format_date(day), callback_data=f"date:{day.isoformat()}")
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="Назад", callback_data="back:service"),
        InlineKeyboardButton(text="Отмена", callback_data="flow:cancel"),
    )
    return builder.as_markup()


def times_kb(times: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for hhmm in times:
        # двоеточие в callback_data не используем: оно разделяет «действие:значение»
        builder.button(text=hhmm, callback_data=f"time:{hhmm.replace(':', '')}")
    builder.adjust(4)
    builder.row(
        InlineKeyboardButton(text="Назад", callback_data="back:date"),
        InlineKeyboardButton(text="Отмена", callback_data="flow:cancel"),
    )
    return builder.as_markup()


def confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить", callback_data="confirm:yes")
    builder.button(text="Назад", callback_data="back:time")
    builder.button(text="Отмена", callback_data="flow:cancel")
    builder.adjust(1, 2)
    return builder.as_markup()


def my_bookings_kb(bookings: list[Booking]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        builder.button(
            text=f"Отменить: {format_date(booking.on_date)} {booking.start_time}",
            callback_data=f"cancel:{booking.id}",
        )
    builder.button(text="Записаться ещё", callback_data="menu:book")
    builder.adjust(1)
    return builder.as_markup()


def cancel_confirm_kb(booking_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, отменить запись", callback_data=f"cancel_yes:{booking_id}")
    builder.button(text="Нет, оставить", callback_data="menu:my")
    builder.adjust(1)
    return builder.as_markup()
