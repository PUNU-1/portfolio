"""Расчёт свободного времени. Чистые функции без базы и Telegram — их легко тестировать."""
from datetime import date, datetime, time, timedelta

from .config import Business


def to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def to_hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def available_days(business: Business, now: datetime) -> list[date]:
    """Даты, на которые можно записаться: от сегодняшней, без выходных."""
    today = now.date()
    days = [today + timedelta(days=i) for i in range(business.days_ahead)]
    return [d for d in days if d.weekday() not in business.days_off]


def free_slots(
    business: Business,
    duration_min: int,
    day: date,
    busy: list[tuple[int, int]],
    now: datetime,
) -> list[str]:
    """Время начала, на которое услуга длиной duration_min помещается и не пересекается с занятым.

    busy — занятые отрезки дня в минутах от полуночи: [(начало, конец), ...].
    """
    day_start = to_minutes(business.work_start)
    day_end = to_minutes(business.work_end)

    result = []
    start = day_start
    while start + duration_min <= day_end:
        end = start + duration_min
        starts_in_future = datetime.combine(day, time(start // 60, start % 60), tzinfo=now.tzinfo) > now
        overlaps = any(start < busy_end and end > busy_start for busy_start, busy_end in busy)
        if starts_in_future and not overlaps:
            result.append(to_hhmm(start))
        start += business.slot_minutes
    return result
