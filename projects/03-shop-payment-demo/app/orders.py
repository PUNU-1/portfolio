"""Заказы и их статусы. Здесь вся бизнес-логика, Flask тут не нужен.

Статусы заказа:
    created — создан, ждёт оплаты
    paid    — оплачен (получено подтверждение от провайдера)
    failed  — оплата не прошла (можно попробовать ещё раз)
"""
import logging
import re
import secrets
import sqlite3
from datetime import datetime, timezone

from . import catalog
from .payments import PaymentEvent

log = logging.getLogger(__name__)

CREATED, PAID, FAILED = "created", "paid", "failed"
MAX_QTY_PER_ITEM = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    """Клиент прислал некорректный заказ (текст можно показать пользователю)."""


class EventRejected(Exception):
    """Подлинное событие, но к нашим данным не подходит (чужой платёж, не та сумма и т.п.)."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_order(db: sqlite3.Connection, items, customer) -> dict:
    """Проверяет заказ и сохраняет его. Цены берём ТОЛЬКО из каталога, а не из запроса клиента."""
    if not isinstance(customer, dict):
        raise ValidationError("Укажите имя и email")
    name = str(customer.get("name", "")).strip()
    email = str(customer.get("email", "")).strip()
    if not 2 <= len(name) <= 80:
        raise ValidationError("Укажите имя (от 2 до 80 символов)")
    if len(email) > 120 or not EMAIL_RE.match(email):
        raise ValidationError("Укажите корректный email")

    if not isinstance(items, list) or not items:
        raise ValidationError("Корзина пуста")

    lines = []  # (товар, количество)
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError("Некорректная позиция заказа")
        product = catalog.find(str(item.get("id", "")))
        qty = item.get("qty")
        if product is None or product.id in seen:
            raise ValidationError("Неизвестный или повторяющийся товар")
        if not isinstance(qty, int) or isinstance(qty, bool) or not 1 <= qty <= MAX_QTY_PER_ITEM:
            raise ValidationError(f"Количество каждого товара — от 1 до {MAX_QTY_PER_ITEM}")
        seen.add(product.id)
        lines.append((product, qty))

    total = sum(product.price_kop * qty for product, qty in lines)
    public_id = secrets.token_urlsafe(9)
    now = _now()

    with db:
        cursor = db.execute(
            """INSERT INTO orders (public_id, customer_name, customer_email, total_kop, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (public_id, name, email, total, CREATED, now, now),
        )
        order_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO order_items (order_id, product_id, title, price_kop, qty) VALUES (?, ?, ?, ?, ?)",
            [(order_id, p.id, p.title, p.price_kop, qty) for p, qty in lines],
        )
    return get_order(db, public_id)


def get_order(db: sqlite3.Connection, public_id: str) -> dict | None:
    order = db.execute("SELECT * FROM orders WHERE public_id = ?", (public_id,)).fetchone()
    if order is None:
        return None
    items = db.execute(
        "SELECT product_id, title, price_kop, qty FROM order_items WHERE order_id = ? ORDER BY id", (order["id"],)
    ).fetchall()
    return {
        "id": order["id"],
        "public_id": order["public_id"],
        "status": order["status"],
        "total_kop": order["total_kop"],
        "customer_name": order["customer_name"],
        "created_at": order["created_at"],
        "items": [dict(item) for item in items],
    }


def public_view(order: dict) -> dict:
    """Что отдаём в браузер: без внутреннего id; email не отдаём вообще."""
    return {key: order[key] for key in ("public_id", "status", "total_kop", "created_at", "items")}


def add_payment(db: sqlite3.Connection, order: dict, provider_name: str, payment_id: str) -> None:
    with db:
        db.execute(
            "INSERT INTO payments (payment_id, order_id, provider, created_at) VALUES (?, ?, ?, ?)",
            (payment_id, order["id"], provider_name, _now()),
        )


def get_payment(db: sqlite3.Connection, payment_id: str) -> sqlite3.Row | None:
    return db.execute(
        """SELECT p.payment_id, p.status AS payment_status, o.public_id, o.total_kop, o.status AS order_status
           FROM payments p JOIN orders o ON o.id = p.order_id WHERE p.payment_id = ?""",
        (payment_id,),
    ).fetchone()


def apply_event(db: sqlite3.Connection, event: PaymentEvent) -> str:
    """Применяет проверенное событие оплаты. Возвращает, что произошло.

    Результаты: "paid", "failed", "duplicate" (событие уже обрабатывали),
    "already_paid" (заказ уже оплачен — повторный платёж не меняет статус).
    """
    payment = get_payment(db, event.payment_id)
    if payment is None:
        raise EventRejected("неизвестный платёж")
    if payment["public_id"] != event.order_public_id:
        raise EventRejected("платёж относится к другому заказу")
    if payment["total_kop"] != event.amount_kop:
        # Главная проверка: даже подлинное событие не должно «оплатить» заказ неверной суммой
        raise EventRejected("сумма платежа не совпадает с суммой заказа")

    with db:  # одна транзакция: либо всё записано, либо ничего
        try:
            db.execute("INSERT INTO webhook_events (event_id, received_at) VALUES (?, ?)", (event.event_id, _now()))
        except sqlite3.IntegrityError:
            return "duplicate"

        db.execute("UPDATE payments SET status = ? WHERE payment_id = ?", (event.status, event.payment_id))

        if payment["order_status"] == PAID:
            if event.status == "succeeded":
                log.warning("Заказ %s оплачен повторно (платёж %s): нужен возврат", event.order_public_id, event.payment_id)
            return "already_paid"

        new_status = PAID if event.status == "succeeded" else FAILED
        db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE public_id = ?",
            (new_status, _now(), event.order_public_id),
        )
        return new_status
