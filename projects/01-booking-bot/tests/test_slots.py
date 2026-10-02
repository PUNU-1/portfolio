from datetime import date, datetime
from zoneinfo import ZoneInfo

from bot.slots import available_days, free_slots, to_hhmm, to_minutes

TZ = ZoneInfo("Europe/Moscow")
MONDAY = date(2030, 1, 7)  # понедельник
SUNDAY = date(2030, 1, 13)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)


def test_minutes_roundtrip():
    assert to_minutes("14:30") == 870
    assert to_hhmm(870) == "14:30"


def test_free_slots_whole_day(business):
    # Рабочий день 10:00–20:00, шаг 30 мин, услуга 60 мин: последняя запись — на 19:00
    slots = free_slots(business, 60, MONDAY, busy=[], now=at(MONDAY, 8))
    assert slots[0] == "10:00"
    assert slots[-1] == "19:00"
    assert len(slots) == 19


def test_busy_interval_blocks_overlapping_starts(business):
    busy = [(to_minutes("12:00"), to_minutes("13:00"))]  # занято 12:00–13:00
    slots = free_slots(business, 60, MONDAY, busy, now=at(MONDAY, 8))
    # 11:30 не подходит: услуга на час закончится в 12:30, это пересечение
    assert "11:00" in slots
    assert "11:30" not in slots
    assert "12:00" not in slots
    assert "12:30" not in slots
    assert "13:00" in slots


def test_longer_service_needs_more_room(business):
    busy = [(to_minutes("12:00"), to_minutes("12:30"))]
    short = free_slots(business, 30, MONDAY, busy, now=at(MONDAY, 8))
    long = free_slots(business, 90, MONDAY, busy, now=at(MONDAY, 8))
    assert "11:30" in short
    assert "11:30" not in long  # 11:30–13:00 накрывает занятое


def test_past_times_are_hidden(business):
    slots = free_slots(business, 30, MONDAY, [], now=at(MONDAY, 14, 10))
    assert slots[0] == "14:30"


def test_available_days_skip_days_off(business):
    days = available_days(business, at(MONDAY, 9))
    assert MONDAY in days
    assert SUNDAY not in days  # воскресенье — выходной в business.json
    assert all(d.weekday() != 6 for d in days)
