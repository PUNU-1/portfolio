import json
import time

import pytest

from app.config import Config
from app.payments.fake import FakePaymentProvider
from app.server import create_app

SECRET = "test-secret-not-a-real-one"
DEFAULT_ITEMS = object()  # «товары не указаны» — чтобы отличать от None, который тоже нужно проверять


@pytest.fixture
def config(tmp_path):
    return Config(
        db_path=str(tmp_path / "shop.db"),
        port=0,
        base_url="http://127.0.0.1:5999",
        provider="fake",
        webhook_secret=SECRET,
    )


@pytest.fixture
def app(config):
    return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def signer(config):
    """Тот же алгоритм подписи, что у «банка»: так тесты изображают провайдера."""
    return FakePaymentProvider(SECRET, config.base_url)


class Shop:
    """Помощник: создаёт заказы и отправляет подписанные webhook."""

    def __init__(self, client, signer):
        self.client = client
        self.signer = signer

    def order(self, items=DEFAULT_ITEMS, name="Иван", email="ivan@example.com"):
        if items is DEFAULT_ITEMS:
            items = [{"id": "tee", "qty": 1}, {"id": "mug", "qty": 2}]
        response = self.client.post("/api/orders", json={"items": items, "customer": {"name": name, "email": email}})
        return response

    def order_with_payment(self, **kwargs):
        response = self.order(**kwargs)
        assert response.status_code == 201, response.get_json()
        data = response.get_json()
        payment_id = data["payment_url"].rsplit("/", 1)[-1]
        return data["order"], payment_id

    def event(self, order, payment_id, kind="payment.succeeded", event_id="evt_1", amount=None):
        return {
            "event_id": event_id,
            "type": kind,
            "payment_id": payment_id,
            "order_id": order["public_id"],
            "amount_kop": order["total_kop"] if amount is None else amount,
        }

    def webhook(self, payload, secret=None, timestamp=None, body=None, signature=None):
        body = body if body is not None else json.dumps(payload).encode()
        timestamp = str(int(time.time())) if timestamp is None else str(timestamp)
        signer = self.signer if secret is None else FakePaymentProvider(secret, "http://x")
        headers = {"X-Timestamp": timestamp, "X-Signature": signature or signer.sign(timestamp, body), "Content-Type": "application/json"}
        return self.client.post("/webhooks/payment", data=body, headers=headers)

    def status(self, order):
        return self.client.get(f"/api/orders/{order['public_id']}").get_json()["order"]["status"]


@pytest.fixture
def shop(client, signer):
    return Shop(client, signer)
