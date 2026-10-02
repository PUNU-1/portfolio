"""Webhook: подпись, повторы, статусы, защита от подделки."""
import time

from tests.conftest import SECRET


def test_valid_signature_marks_order_paid(shop):
    order, payment_id = shop.order_with_payment()
    response = shop.webhook(shop.event(order, payment_id))
    assert response.status_code == 200
    assert response.get_json()["result"] == "paid"
    assert shop.status(order) == "paid"


def test_failed_event_marks_order_failed(shop):
    order, payment_id = shop.order_with_payment()
    assert shop.webhook(shop.event(order, payment_id, kind="payment.failed")).status_code == 200
    assert shop.status(order) == "failed"


def test_wrong_secret_is_rejected(shop):
    order, payment_id = shop.order_with_payment()
    response = shop.webhook(shop.event(order, payment_id), secret="not-the-real-secret")
    assert response.status_code == 400
    assert shop.status(order) == "created"


def test_garbage_signature_is_rejected(shop):
    order, payment_id = shop.order_with_payment()
    response = shop.webhook(shop.event(order, payment_id), signature="deadbeef")
    assert response.status_code == 400
    assert shop.status(order) == "created"


def test_tampered_body_is_rejected(shop, signer):
    """Подпись снята с одного тела, а отправлено другое (например, сумму поменяли) — отказ."""
    order, payment_id = shop.order_with_payment()
    timestamp = str(int(time.time()))
    original = b'{"event_id":"evt_x","type":"payment.failed","payment_id":"p","order_id":"o","amount_kop":1}'
    signature = signer.sign(timestamp, original)
    tampered = original.replace(b"payment.failed", b"payment.succeeded")
    response = shop.webhook(None, body=tampered, timestamp=timestamp, signature=signature)
    assert response.status_code == 400
    assert shop.status(order) == "created"


def test_missing_headers_are_rejected(shop, client):
    order, payment_id = shop.order_with_payment()
    response = client.post("/webhooks/payment", json=shop.event(order, payment_id))
    assert response.status_code == 400
    assert shop.status(order) == "created"


def test_stale_timestamp_is_rejected(shop):
    """Перехваченный webhook нельзя прислать повторно спустя время."""
    order, payment_id = shop.order_with_payment()
    old = int(time.time()) - 3600
    response = shop.webhook(shop.event(order, payment_id), timestamp=old)
    assert response.status_code == 400
    assert shop.status(order) == "created"


def test_duplicate_event_is_processed_once(shop):
    order, payment_id = shop.order_with_payment()
    payload = shop.event(order, payment_id, event_id="evt_same")
    assert shop.webhook(payload).get_json()["result"] == "paid"
    assert shop.webhook(payload).get_json()["result"] == "duplicate"
    assert shop.status(order) == "paid"


def test_wrong_amount_is_not_applied_even_with_valid_signature(shop):
    order, payment_id = shop.order_with_payment()
    response = shop.webhook(shop.event(order, payment_id, amount=100))
    assert response.status_code == 422
    assert shop.status(order) == "created"


def test_unknown_payment_is_rejected(shop):
    order, _ = shop.order_with_payment()
    response = shop.webhook(shop.event(order, "fake_unknown"))
    assert response.status_code == 422


def test_payment_for_other_order_is_rejected(shop):
    order_a, payment_a = shop.order_with_payment()
    order_b, _ = shop.order_with_payment()
    response = shop.webhook(shop.event(order_b, payment_a))  # платёж от заказа A, а в событии заказ B
    assert response.status_code == 422
    assert shop.status(order_b) == "created"


def test_retry_after_failure_can_succeed(shop, client):
    order, first_payment = shop.order_with_payment()
    shop.webhook(shop.event(order, first_payment, kind="payment.failed", event_id="evt_a"))
    assert shop.status(order) == "failed"

    second_payment = client.post(f"/api/orders/{order['public_id']}/pay").get_json()["payment_url"].rsplit("/", 1)[-1]
    shop.webhook(shop.event(order, second_payment, event_id="evt_b"))
    assert shop.status(order) == "paid"


def test_paid_order_stays_paid_after_late_failure(shop, client):
    order, first_payment = shop.order_with_payment()
    second_payment = client.post(f"/api/orders/{order['public_id']}/pay").get_json()["payment_url"].rsplit("/", 1)[-1]
    shop.webhook(shop.event(order, second_payment, event_id="evt_ok"))
    response = shop.webhook(shop.event(order, first_payment, kind="payment.failed", event_id="evt_late_fail"))
    assert response.get_json()["result"] == "already_paid"
    assert shop.status(order) == "paid"


def test_cannot_pay_already_paid_order(shop, client):
    order, payment_id = shop.order_with_payment()
    shop.webhook(shop.event(order, payment_id))
    assert client.post(f"/api/orders/{order['public_id']}/pay").status_code == 409


def test_secret_is_not_in_source():
    """Секрет подписи берётся из .env, а в исходниках приложения его нет."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "app"
    assert all(SECRET not in path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
