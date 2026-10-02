"""Хранение записей в SQLite."""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone

import aiosqlite

from .config import Service
from .slots import to_hhmm, to_minutes

SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    user_name    TEXT NOT NULL,
    service_id   TEXT NOT NULL,
    service_name TEXT NOT NULL,
    price        INTEGER NOT NULL,
    date         TEXT NOT NULL,      -- 2025-01-31
    start_time   TEXT NOT NULL,      -- 14:30
    duration_min INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',   -- active / cancelled
    created_at   TEXT NOT NULL
);
-- Вторая линия защиты от двойной записи на одно и то же время
CREATE UNIQUE INDEX IF NOT EXISTS ux_active_slot
    ON bookings (date, start_time) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_bookings_user ON bookings (user_id, status);
"""


class SlotTaken(Exception):
    """Время уже занято (или пересекается с другой записью)."""


class TooManyBookings(Exception):
    """У клиента уже максимум активных записей."""


@dataclass(frozen=True)
class Booking:
    id: int
    user_id: int
    user_name: str
    service_id: str
    service_name: str
    price: int
    day: str
    start_time: str
    duration_min: int
    status: str

    @property
    def end_time(self) -> str:
        return to_hhmm(to_minutes(self.start_time) + self.duration_min)

    @property
    def on_date(self) -> date:
        return date.fromisoformat(self.day)

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> "Booking":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            user_name=row["user_name"],
            service_id=row["service_id"],
            service_name=row["service_name"],
            price=row["price"],
            day=row["date"],
            start_time=row["start_time"],
            duration_min=row["duration_min"],
            status=row["status"],
        )


class Database:
    def __init__(self, path: str):
        self.path = path

    @asynccontextmanager
    async def _connect(self):
        # isolation_level=None — транзакциями управляем сами (BEGIN/COMMIT ниже)
        async with aiosqlite.connect(self.path, isolation_level=None, timeout=10) as conn:
            conn.row_factory = aiosqlite.Row
            yield conn

    async def init(self) -> None:
        async with self._connect() as conn:
            await conn.executescript(SCHEMA)

    async def create_booking(
        self,
        *,
        user_id: int,
        user_name: str,
        service: Service,
        day: date,
        start_time: str,
        today: date,
        max_active: int,
    ) -> Booking:
        """Создаёт запись или бросает SlotTaken / TooManyBookings.

        BEGIN IMMEDIATE блокирует запись в БД на время проверки,
        поэтому два клиента не займут одно время одновременно.
        """
        start = to_minutes(start_time)
        end = start + service.duration_min

        async with self._connect() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM bookings WHERE user_id = ? AND status = 'active' AND date >= ?",
                    (user_id, today.isoformat()),
                )
                (active_count,) = await cursor.fetchone()
                if active_count >= max_active:
                    raise TooManyBookings

                cursor = await conn.execute(
                    "SELECT start_time, duration_min FROM bookings WHERE date = ? AND status = 'active'",
                    (day.isoformat(),),
                )
                for row in await cursor.fetchall():
                    busy_start = to_minutes(row["start_time"])
                    busy_end = busy_start + row["duration_min"]
                    if start < busy_end and end > busy_start:
                        raise SlotTaken

                cursor = await conn.execute(
                    """INSERT INTO bookings
                       (user_id, user_name, service_id, service_name, price, date, start_time,
                        duration_min, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        user_id,
                        user_name,
                        service.id,
                        service.name,
                        service.price,
                        day.isoformat(),
                        start_time,
                        service.duration_min,
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
                booking_id = cursor.lastrowid
                await conn.execute("COMMIT")
            except BaseException:
                await conn.execute("ROLLBACK")
                raise

        booking = await self.get(booking_id)
        assert booking is not None
        return booking

    async def get(self, booking_id: int) -> Booking | None:
        async with self._connect() as conn:
            cursor = await conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
            row = await cursor.fetchone()
        return Booking.from_row(row) if row else None

    async def user_bookings(self, user_id: int, today: date) -> list[Booking]:
        """Активные записи клиента, начиная с сегодняшнего дня."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                """SELECT * FROM bookings
                   WHERE user_id = ? AND status = 'active' AND date >= ?
                   ORDER BY date, start_time""",
                (user_id, today.isoformat()),
            )
            rows = await cursor.fetchall()
        return [Booking.from_row(row) for row in rows]

    async def cancel(self, booking_id: int, user_id: int) -> Booking | None:
        """Отменяет запись, только если она принадлежит этому клиенту и ещё активна."""
        async with self._connect() as conn:
            cursor = await conn.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE id = ? AND user_id = ? AND status = 'active'",
                (booking_id, user_id),
            )
            if cursor.rowcount == 0:
                return None
        return await self.get(booking_id)

    async def bookings_on(self, day: date) -> list[Booking]:
        async with self._connect() as conn:
            cursor = await conn.execute(
                "SELECT * FROM bookings WHERE date = ? AND status = 'active' ORDER BY start_time",
                (day.isoformat(),),
            )
            rows = await cursor.fetchall()
        return [Booking.from_row(row) for row in rows]

    async def busy_intervals(self, days: list[date]) -> dict[date, list[tuple[int, int]]]:
        """Занятые отрезки времени по каждому из дней: {день: [(начало, конец), ...]} в минутах."""
        result: dict[date, list[tuple[int, int]]] = {d: [] for d in days}
        if not days:
            return result
        async with self._connect() as conn:
            cursor = await conn.execute(
                """SELECT date, start_time, duration_min FROM bookings
                   WHERE status = 'active' AND date BETWEEN ? AND ?""",
                (min(days).isoformat(), max(days).isoformat()),
            )
            rows = await cursor.fetchall()
        for row in rows:
            day = date.fromisoformat(row["date"])
            if day in result:
                start = to_minutes(row["start_time"])
                result[day].append((start, start + row["duration_min"]))
        return result
