from ..config import Config
from .base import InvalidWebhook, PaymentEvent, PaymentProvider, PaymentSession
from .fake import FakePaymentProvider

__all__ = ["InvalidWebhook", "PaymentEvent", "PaymentProvider", "PaymentSession", "FakePaymentProvider", "get_provider"]


def get_provider(config: Config) -> PaymentProvider:
    """Выбирает адаптер по PAYMENT_PROVIDER из .env. Новый провайдер добавляется здесь одной веткой."""
    if config.provider == "fake":
        return FakePaymentProvider(config.webhook_secret, config.base_url, config.webhook_tolerance_sec)
    raise SystemExit(
        f"Платёжный провайдер «{config.provider}» не подключён. "
        "Сейчас доступен только fake (тестовая оплата). Как добавить реальный — в README."
    )
