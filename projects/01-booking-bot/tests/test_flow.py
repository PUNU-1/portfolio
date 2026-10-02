"""Сквозные тесты: настоящий диалог через aiogram, но вместо Telegram — FakeSession."""
from datetime import timedelta

from aiogram.methods import AnswerCallbackQuery

from bot.slots import available_days
from tests.conftest import CLIENT_ID, OWNER_ID, Client


def next_working_day(business):
    """Ближайший будущий рабочий день (не сегодня, чтобы не зависеть от времени запуска теста)."""
    now = business.now()
    return next(d for d in available_days(business, now + timedelta(days=1)) if d > now.date())


async def make_booking(client, business, service_id="haircut", time_button="time:1200"):
    day = next_working_day(business)
    await client.send("/start")
    await client.press("menu:book")
    await client.press(f"svc:{service_id}")
    await client.press(f"date:{day.isoformat()}")
    await client.press(time_button)
    await client.press("confirm:yes")
    return day


async def test_start_shows_welcome_and_demo_notice(client, session):
    await client.send("/start")
    text = session.sent_texts(CLIENT_ID)[-1]
    assert "Борода (демо)" in text
    assert "демо-проект" in text


async def test_full_booking_flow(client, session, db, business):
    day = await make_booking(client, business)

    saved = await db.user_bookings(CLIENT_ID, business.now().date())
    assert len(saved) == 1
    assert saved[0].day == day.isoformat()
    assert saved[0].start_time == "12:00"
    assert saved[0].service_id == "haircut"

    # клиент получил подтверждение, владелец — уведомление
    assert any("Вы записаны" in t for t in session.sent_texts())
    owner_msgs = session.sent_texts(OWNER_ID)
    assert len(owner_msgs) == 1 and "Новая запись" in owner_msgs[0]


async def test_my_bookings_and_cancel(client, session, db, business):
    await make_booking(client, business)
    booking = (await db.user_bookings(CLIENT_ID, business.now().date()))[0]

    await client.send("/my_bookings")
    assert "Ваши записи" in session.sent_texts(CLIENT_ID)[-1]

    await client.press(f"cancel:{booking.id}")  # спрашивает подтверждение
    assert (await db.get(booking.id)).status == "active"
    await client.press(f"cancel_yes:{booking.id}")
    assert (await db.get(booking.id)).status == "cancelled"
    assert any("Отмена записи" in t for t in session.sent_texts(OWNER_ID))


async def test_cancel_command_aborts_flow_in_progress(client, session, business):
    await client.send("/start")
    await client.press("menu:book")
    await client.send("/cancel")
    assert "Запись прервана" in session.sent_texts(CLIENT_ID)[-1]


async def test_cancel_command_without_flow_shows_bookings(client, session, business):
    await make_booking(client, business)
    await client.send("/cancel")
    assert "Ваши записи" in session.sent_texts(CLIENT_ID)[-1]


async def test_second_client_cannot_take_same_time(dp, bot, session, db, business):
    first = Client(dp, bot, user_id=301, name="Первый")
    second = Client(dp, bot, user_id=302, name="Второй")
    day = await make_booking(first, business)

    # второй добирается до выбора времени
    await second.send("/start")
    await second.press("menu:book")
    await second.press("svc:haircut")
    await second.press(f"date:{day.isoformat()}")
    session.calls.clear()
    await second.press("time:1200")  # это время уже занято

    alerts = [c for c in session.calls if isinstance(c, AnswerCallbackQuery) and c.show_alert]
    assert alerts and "занято" in alerts[0].text
    assert await db.user_bookings(302, business.now().date()) == []


async def test_today_command_admin_only(client, dp, bot, session, business):
    owner = Client(dp, bot, user_id=OWNER_ID, name="Владелец")

    await client.send("/today")
    assert "только для администратора" in session.sent_texts(CLIENT_ID)[-1]

    await owner.send("/today")
    assert "записей нет" in session.sent_texts(OWNER_ID)[-1]


async def test_stale_button_gets_friendly_answer(client, session):
    await client.press("svc:haircut")  # состояние не начато — как после перезапуска бота
    alerts = [c for c in session.calls if isinstance(c, AnswerCallbackQuery)]
    assert alerts and "устарела" in alerts[0].text
