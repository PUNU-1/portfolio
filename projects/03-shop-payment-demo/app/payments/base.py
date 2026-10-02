"""Интерфейс платёжного адаптера.

Остальной код магазина знает только про этот интерфейс. Чтобы подключить настоящую
платёжную систему, нужно написать новый класс-наследник PaymentProvider (см. README)
и ничего больше в магазине не менять.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Mapping


class InvalidWebhook(Exception):
    """Webhook не прошёл проверку подлинности или имеет неверный формат."""


@dataclass(frozen=True)
class PaymentSession:
    """Результат создания платежа."""

    payment_id: str  # идентификатор платежа у провайдера
    payment_url: str  # куда отправить покупателя, чтобы он заплатил


@dataclass(frozen=True)
class PaymentEvent:
    """Проверенное событие от провайдера, приведённое к общему виду."""

    event_id: str  # уникален для события: по нему отсекаем повторные доставки
    status: Literal["succeeded", "failed"]
    payment_id: str
    order_public_id: str
    amount_kop: int


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_payment(self, order_public_id: str, amount_kop: int, description: str, return_url: str) -> PaymentSession:
        """Создаёт платёж у провайдера и возвращает ссылку на оплату."""

    @abstractmethod
    def parse_webhook(self, headers: Mapping[str, str], body: bytes) -> PaymentEvent:
        """Проверяет подлинность webhook и превращает его в PaymentEvent.

        Если подпись неверна — бросает InvalidWebhook. Подпись надо проверять по сырым байтам тела,
        до разбора JSON: иначе её не получится воспроизвести.
        """
