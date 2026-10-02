"""Заглушка «тестовая оплата»: ничего не списывает, но ведёт себя как настоящая интеграция.

Схема подписи webhook (по образцу многих провайдеров):
    X-Timestamp: время отправки, секунды Unix
    X-Signature: HMAC-SHA256(секрет, "<X-Timestamp>.<тело запроса>") в hex
Метка времени входит в подпись, поэтому перехваченный webhook нельзя отправить повторно позже.
"""
import hashlib
import hmac
import json
import secrets
import time
from typing import Mapping

from .base import InvalidWebhook, PaymentEvent, PaymentProvider, PaymentSession


class FakePaymentProvider(PaymentProvider):
    name = "fake"

    def __init__(self, secret: str, base_url: str, tolerance_sec: int = 300):
        self.secret = secret
        self.base_url = base_url
        self.tolerance_sec = tolerance_sec

    def create_payment(self, order_public_id: str, amount_kop: int, description: str, return_url: str) -> PaymentSession:
        payment_id = "fake_" + secrets.token_hex(8)
        # Страница «банка» — наша же заглушка (app/payments/fake_gateway.py).
        # return_url заглушка не использует: после оплаты она ведёт на страницу заказа.
        return PaymentSession(payment_id=payment_id, payment_url=f"{self.base_url}/fake-gateway/{payment_id}")

    # --- подпись ---

    def sign(self, timestamp: str, body: bytes) -> str:
        message = timestamp.encode() + b"." + body
        return hmac.new(self.secret.encode(), message, hashlib.sha256).hexdigest()

    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> PaymentEvent:
        timestamp = headers.get("X-Timestamp", "")
        signature = headers.get("X-Signature", "")

        if not timestamp.isdigit() or abs(time.time() - int(timestamp)) > self.tolerance_sec:
            raise InvalidWebhook("нет метки времени или она устарела")

        # compare_digest сравнивает за постоянное время: по скорости ответа подпись не подобрать
        if not hmac.compare_digest(self.sign(timestamp, body), signature):
            raise InvalidWebhook("неверная подпись")

        try:
            data = json.loads(body)
            status = {"payment.succeeded": "succeeded", "payment.failed": "failed"}[data["type"]]
            return PaymentEvent(
                event_id=str(data["event_id"]),
                status=status,
                payment_id=str(data["payment_id"]),
                order_public_id=str(data["order_id"]),
                amount_kop=int(data["amount_kop"]),
            )
        except (ValueError, KeyError, TypeError) as error:
            raise InvalidWebhook(f"некорректное тело webhook: {error!r}") from error
