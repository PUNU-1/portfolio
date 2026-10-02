"""Настройки: секреты берём из .env, данные бизнеса — из business.json."""
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    price: int
    duration_min: int


@dataclass(frozen=True)
class Business:
    name: str
    address: str
    phone: str
    timezone: str
    work_start: str  # "10:00"
    work_end: str  # "20:00"
    slot_minutes: int  # шаг сетки времени
    days_ahead: int  # на сколько дней вперёд можно записаться
    days_off: tuple[int, ...]  # выходные: 0 = понедельник ... 6 = воскресенье
    max_active_bookings: int  # сколько активных записей может быть у одного клиента
    demo_notice: str
    services: tuple[Service, ...]

    def service(self, service_id: str) -> Service | None:
        for service in self.services:
            if service.id == service_id:
                return service
        return None

    def now(self) -> datetime:
        """Текущее время в часовом поясе бизнеса (сервер может стоять где угодно)."""
        return datetime.now(ZoneInfo(self.timezone))


@dataclass(frozen=True)
class Settings:
    bot_token: str
    owner_id: int  # получает уведомления о записях
    admin_ids: frozenset[int]  # кто может вызвать /today (владелец входит всегда)
    db_path: str


def load_business(path: Path = BASE_DIR / "business.json") -> Business:
    raw = json.loads(path.read_text(encoding="utf-8"))
    services = tuple(Service(**item) for item in raw.pop("services"))
    return Business(
        name=raw["name"],
        address=raw["address"],
        phone=raw["phone"],
        timezone=raw["timezone"],
        work_start=raw["work_start"],
        work_end=raw["work_end"],
        slot_minutes=raw["slot_minutes"],
        days_ahead=raw["days_ahead"],
        days_off=tuple(raw["days_off"]),
        max_active_bookings=raw["max_active_bookings_per_user"],
        demo_notice=raw.get("demo_notice", ""),
        services=services,
    )


def load_settings() -> Settings:
    load_dotenv(BASE_DIR / ".env")

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token == "put_your_token_here":
        raise SystemExit(
            "Не задан BOT_TOKEN. Создайте бота у @BotFather, "
            "впишите токен в файл .env (образец — .env.example)."
        )

    owner_raw = os.getenv("OWNER_ID", "").strip()
    if not owner_raw.isdigit():
        raise SystemExit(
            "Не задан OWNER_ID. Узнайте свой Telegram ID у @userinfobot "
            "и впишите числом в файл .env."
        )
    owner_id = int(owner_raw)

    extra_admins = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}

    return Settings(
        bot_token=token,
        owner_id=owner_id,
        admin_ids=frozenset(extra_admins | {owner_id}),
        db_path=os.getenv("DB_PATH", str(BASE_DIR / "bookings.db")),
    )
