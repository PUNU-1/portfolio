"""Диалог записи: услуга -> дата -> время -> подтверждение. А также «мои записи» и отмена."""
from datetime import date
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from .. import keyboards
from ..config import Business, Settings
from ..db import Database, SlotTaken, TooManyBookings
from ..formatting import format_booking, format_date, user_display_name, user_link
from ..notify import notify_owner
from ..slots import available_days, free_slots, to_hhmm, to_minutes

router = Router()


class BookingFlow(StatesGroup):
    service = State()
    day = State()
    time = State()
    confirm = State()


async def show(event: Message | CallbackQuery, text: str, markup=None) -> None:
    """Отвечает на команду новым сообщением, а на нажатие кнопки — правит старое."""
    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            try:
                await event.message.edit_text(text, reply_markup=markup)
            except TelegramBadRequest:
                pass  # «message is not modified» — текст тот же, это не ошибка
        await event.answer()
    else:
        await event.answer(text, reply_markup=markup)


def welcome_text(business: Business) -> str:
    text = (
        f"Здравствуйте! Это бот записи «{escape(business.name)}».\n"
        f"{escape(business.address)}\n{escape(business.phone)}\n\n"
        "Команды: /book — записаться, /my_bookings — мои записи, /cancel — отмена."
    )
    if business.demo_notice:
        text += f"\n\n<i>{escape(business.demo_notice)}</i>"
    return text


# ---------- старт и меню ----------


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, business: Business) -> None:
    await state.clear()
    await message.answer(welcome_text(business), reply_markup=keyboards.main_menu())


@router.message(Command("book"))
@router.callback_query(F.data == "menu:book")
async def begin_booking(event: Message | CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    await state.clear()
    active = await db.user_bookings(event.from_user.id, business.now().date())
    if len(active) >= business.max_active_bookings:
        await show(
            event,
            f"У вас уже максимум активных записей ({len(active)}). "
            "Отмените одну из них в /my_bookings, чтобы записаться снова.",
        )
        return
    await state.set_state(BookingFlow.service)
    await show(event, "Выберите услугу:", keyboards.services_kb(business))


# ---------- шаги диалога ----------


async def show_dates(event: Message | CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    data = await state.get_data()
    service = business.service(data["service_id"])
    now = business.now()
    days = available_days(business, now)
    busy = await db.busy_intervals(days)
    free_days = [d for d in days if free_slots(business, service.duration_min, d, busy[d], now)]

    await state.set_state(BookingFlow.day)
    text = f"<b>{escape(service.name)}</b>\nВыберите дату:" if free_days else "Свободных дат пока нет, загляните позже."
    await show(event, text, keyboards.dates_kb(free_days))


async def show_times(event: Message | CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    data = await state.get_data()
    service = business.service(data["service_id"])
    day = date.fromisoformat(data["day"])
    now = business.now()
    busy = await db.busy_intervals([day])
    times = free_slots(business, service.duration_min, day, busy[day], now)

    if not times:  # пока клиент выбирал, всё время заняли
        await show_dates(event, state, db, business)
        return
    await state.set_state(BookingFlow.time)
    await show(event, f"<b>{format_date(day)}</b>\nВыберите время начала:", keyboards.times_kb(times))


@router.callback_query(BookingFlow.service, F.data.startswith("svc:"))
async def choose_service(cb: CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    service = business.service(cb.data.removeprefix("svc:"))
    if service is None:
        await cb.answer("Такой услуги нет", show_alert=True)
        return
    await state.update_data(service_id=service.id)
    await show_dates(cb, state, db, business)


@router.callback_query(BookingFlow.day, F.data.startswith("date:"))
async def choose_date(cb: CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    await state.update_data(day=cb.data.removeprefix("date:"))
    await show_times(cb, state, db, business)


@router.callback_query(BookingFlow.time, F.data.startswith("time:"))
async def choose_time(cb: CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    raw = cb.data.removeprefix("time:")  # "1430"
    start_time = f"{raw[:2]}:{raw[2:]}"

    data = await state.get_data()
    service = business.service(data["service_id"])
    day = date.fromisoformat(data["day"])
    busy = await db.busy_intervals([day])
    if start_time not in free_slots(business, service.duration_min, day, busy[day], business.now()):
        await cb.answer("Это время уже занято, выберите другое", show_alert=True)
        await show_times(cb, state, db, business)
        return

    await state.update_data(start_time=start_time)
    await state.set_state(BookingFlow.confirm)
    text = (
        "<b>Проверьте запись</b>\n\n"
        f"{escape(service.name)} · {service.price} ₽\n"
        f"{format_date(day)}, {start_time}–{to_hhmm(to_minutes(start_time) + service.duration_min)}\n\n"
        f"{escape(business.address)}"
    )
    await show(cb, text, keyboards.confirm_kb())


@router.callback_query(BookingFlow.confirm, F.data == "confirm:yes")
async def confirm_booking(
    cb: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    db: Database,
    business: Business,
    settings: Settings,
) -> None:
    data = await state.get_data()
    service = business.service(data["service_id"])
    day = date.fromisoformat(data["day"])

    try:
        booking = await db.create_booking(
            user_id=cb.from_user.id,
            user_name=user_display_name(cb.from_user),
            service=service,
            day=day,
            start_time=data["start_time"],
            today=business.now().date(),
            max_active=business.max_active_bookings,
        )
    except SlotTaken:
        await cb.answer("Это время только что заняли", show_alert=True)
        await show_times(cb, state, db, business)
        return
    except TooManyBookings:
        await state.clear()
        await show(cb, "У вас уже максимум активных записей. Отмените одну в /my_bookings.")
        return

    await state.clear()
    await show(
        cb,
        f"<b>Вы записаны</b>\n\n{format_booking(booking)}\n\n{escape(business.address)}\n"
        "Отменить или посмотреть записи: /my_bookings",
    )
    await notify_owner(
        bot, settings, f"<b>Новая запись #{booking.id}</b>\n{format_booking(booking)}\nКлиент: {user_link(booking)}"
    )


# ---------- «назад» и отмена диалога ----------


@router.callback_query(BookingFlow.day, F.data == "back:service")
async def back_to_service(cb: CallbackQuery, state: FSMContext, business: Business) -> None:
    await state.set_state(BookingFlow.service)
    await show(cb, "Выберите услугу:", keyboards.services_kb(business))


@router.callback_query(BookingFlow.time, F.data == "back:date")
async def back_to_date(cb: CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    await show_dates(cb, state, db, business)


@router.callback_query(BookingFlow.confirm, F.data == "back:time")
async def back_to_time(cb: CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    await show_times(cb, state, db, business)


@router.callback_query(F.data == "flow:cancel")
async def abort_flow(cb: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show(cb, "Запись прервана. Начать заново: /book", keyboards.main_menu())


# ---------- мои записи и отмена записи ----------


async def show_my_bookings(event: Message | CallbackQuery, db: Database, business: Business) -> None:
    bookings = await db.user_bookings(event.from_user.id, business.now().date())
    if not bookings:
        await show(event, "У вас нет активных записей.", keyboards.main_menu())
        return
    lines = ["<b>Ваши записи</b>", ""]
    for number, booking in enumerate(bookings, start=1):
        lines.append(f"{number}. {format_booking(booking)}\n")
    await show(event, "\n".join(lines), keyboards.my_bookings_kb(bookings))


@router.message(Command("my_bookings"))
@router.callback_query(F.data == "menu:my")
async def my_bookings(event: Message | CallbackQuery, state: FSMContext, db: Database, business: Business) -> None:
    await state.clear()
    await show_my_bookings(event, db, business)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, db: Database, business: Business) -> None:
    """Во время записи — прерывает её, в остальное время — предлагает отменить одну из записей."""
    if await state.get_state() is not None:
        await state.clear()
        await message.answer("Запись прервана. Начать заново: /book", reply_markup=keyboards.main_menu())
        return
    await show_my_bookings(message, db, business)


@router.callback_query(F.data.startswith("cancel:"))
async def ask_cancel_confirmation(cb: CallbackQuery, db: Database) -> None:
    booking = await db.get(int(cb.data.removeprefix("cancel:")))
    if booking is None or booking.user_id != cb.from_user.id or booking.status != "active":
        await cb.answer("Запись не найдена или уже отменена", show_alert=True)
        return
    await show(cb, f"Отменить запись?\n\n{format_booking(booking)}", keyboards.cancel_confirm_kb(booking.id))


@router.callback_query(F.data.startswith("cancel_yes:"))
async def do_cancel(cb: CallbackQuery, bot: Bot, db: Database, settings: Settings) -> None:
    booking = await db.cancel(int(cb.data.removeprefix("cancel_yes:")), cb.from_user.id)
    if booking is None:
        await cb.answer("Запись не найдена или уже отменена", show_alert=True)
        return
    await show(cb, "Запись отменена. Записаться снова: /book", keyboards.main_menu())
    await notify_owner(
        bot, settings, f"<b>Отмена записи #{booking.id}</b>\n{format_booking(booking)}\nКлиент: {user_link(booking)}"
    )
