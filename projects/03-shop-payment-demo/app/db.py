"""SQLite: заказы, их позиции, платежи и уже обработанные webhook-события."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    public_id      TEXT NOT NULL UNIQUE,   -- случайный код для ссылок (подобрать чужой заказ нельзя)
    customer_name  TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    total_kop      INTEGER NOT NULL,
    status         TEXT NOT NULL DEFAULT 'created',   -- created / paid / failed
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id   INTEGER NOT NULL REFERENCES orders (id),
    product_id TEXT NOT NULL,
    title      TEXT NOT NULL,
    price_kop  INTEGER NOT NULL,   -- цена на момент заказа
    qty        INTEGER NOT NULL
);

-- У заказа может быть несколько попыток оплаты (первая не прошла — клиент пробует снова)
CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,   -- id платежа у провайдера
    order_id   INTEGER NOT NULL REFERENCES orders (id),
    provider   TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',   -- pending / succeeded / failed
    created_at TEXT NOT NULL
);

-- Провайдеры могут присылать одно событие повторно: запоминаем обработанные
CREATE TABLE IF NOT EXISTS webhook_events (
    event_id    TEXT PRIMARY KEY,
    received_at TEXT NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: str) -> None:
    conn = connect(path)
    with conn:
        conn.executescript(SCHEMA)
    conn.close()
