import asyncio
from datetime import date

import pytest

from bot.db import SlotTaken, TooManyBookings

DAY = date(2030, 1, 7)
TODAY = date(2030, 1, 1)


async def book(db, business, user_id, service_id, start, day=DAY, max_active=3):
    return await db.create_booking(
        user_id=user_id,
        user_name=f"user{user_id}",
        service=business.service(service_id),
        day=day,
        start_time=start,
        today=TODAY,
        max_active=max_active,
    )


async def test_create_and_read(db, business):
    booking = await book(db, business, 1, "haircut", "12:00")
    assert booking.start_time == "12:00"
    assert booking.end_time == "13:00"  # стрижка 60 минут
    assert booking.status == "active"
    assert [b.id for b in await db.user_bookings(1, TODAY)] == [booking.id]


async def test_same_time_is_rejected(db, business):
    await book(db, business, 1, "haircut", "12:00")
    with pytest.raises(SlotTaken):
        await book(db, business, 2, "haircut", "12:00")


async def test_overlapping_time_is_rejected(db, business):
    await book(db, business, 1, "haircut", "12:00")  # 12:00–13:00
    with pytest.raises(SlotTaken):
        await book(db, business, 2, "beard", "12:30")  # 12:30–13:00 пересекается
    await book(db, business, 2, "beard", "13:00")  # встык — можно


async def test_two_clients_at_once_only_one_wins(db, business):
    results = await asyncio.gather(
        book(db, business, 1, "haircut", "15:00"),
        book(db, business, 2, "haircut", "15:00"),
        return_exceptions=True,
    )
    wins = [r for r in results if not isinstance(r, Exception)]
    fails = [r for r in results if isinstance(r, SlotTaken)]
    assert len(wins) == 1 and len(fails) == 1


async def test_limit_of_active_bookings(db, business):
    await book(db, business, 1, "beard", "10:00", max_active=2)
    await book(db, business, 1, "beard", "11:00", max_active=2)
    with pytest.raises(TooManyBookings):
        await book(db, business, 1, "beard", "12:00", max_active=2)


async def test_cancel_frees_the_slot(db, business):
    booking = await book(db, business, 1, "haircut", "12:00")
    cancelled = await db.cancel(booking.id, user_id=1)
    assert cancelled.status == "cancelled"
    assert await db.user_bookings(1, TODAY) == []
    await book(db, business, 2, "haircut", "12:00")  # время снова свободно


async def test_cannot_cancel_someone_elses_booking(db, business):
    booking = await book(db, business, 1, "haircut", "12:00")
    assert await db.cancel(booking.id, user_id=999) is None
    assert (await db.get(booking.id)).status == "active"


async def test_bookings_on_day_sorted(db, business):
    await book(db, business, 1, "beard", "16:00")
    await book(db, business, 2, "beard", "11:00")
    assert [b.start_time for b in await db.bookings_on(DAY)] == ["11:00", "16:00"]


async def test_busy_intervals(db, business):
    await book(db, business, 1, "haircut", "12:00")
    busy = await db.busy_intervals([DAY, date(2030, 1, 8)])
    assert busy[DAY] == [(720, 780)]
    assert busy[date(2030, 1, 8)] == []
