"""Настройки из .env (образец — .env.example). Секреты в коде не хранятся."""
import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    db_path: str
    port: int
    base_url: str  # публичный адрес сайта; по нему заглушка шлёт webhook самой себе
    provider: str  # какой платёжный адаптер включён
    webhook_secret: str  # общий секрет для подписи webhook
    webhook_tolerance_sec: int = 300  # насколько «старым» может быть webhook (защита от повтора)
    secret_was_generated: bool = False


def load_config() -> Config:
    load_dotenv(BASE_DIR / ".env")

    port = int(os.getenv("PORT", "5050"))
    secret = os.getenv("PAYMENT_WEBHOOK_SECRET", "").strip()
    generated = not secret
    if generated:
        # Для заглушки подойдёт случайный секрет на время работы процесса:
        # и «банк», и магазин — это одна и та же программа. Для настоящего провайдера секрет задаётся в .env.
        secret = secrets.token_hex(32)

    return Config(
        db_path=os.getenv("DB_PATH", str(BASE_DIR / "shop.db")),
        port=port,
        base_url=(os.getenv("BASE_URL", "").strip() or f"http://127.0.0.1:{port}").rstrip("/"),
        provider=os.getenv("PAYMENT_PROVIDER", "fake").strip().lower(),
        webhook_secret=secret,
        secret_was_generated=generated,
    )
