"""Страница «банка» для заглушки: имитирует платёжную страницу провайдера.

Это часть ЗАГЛУШКИ. При подключении настоящей платёжной системы эта страница не нужна:
покупателя будет принимать сайт провайдера, а webhook пришлёт сам провайдер.
"""
import json
import secrets
import time
import urllib.error
import urllib.request

from flask import Blueprint, abort, redirect, render_template

from .. import orders
from .fake import FakePaymentProvider


def make_blueprint(provider: FakePaymentProvider, get_db) -> Blueprint:
    bp = Blueprint("fake_gateway", __name__)

    @bp.get("/fake-gateway/<payment_id>")
    def page(payment_id: str):
        payment = orders.get_payment(get_db(), payment_id)
        if payment is None:
            abort(404)
        return render_template("fake_gateway.html", payment=payment)

    @bp.post("/fake-gateway/<payment_id>/<outcome>")
    def complete(payment_id: str, outcome: str):
        payment = orders.get_payment(get_db(), payment_id)
        if payment is None or outcome not in ("success", "fail"):
            abort(404)

        body = json.dumps(
            {
                "event_id": "evt_" + secrets.token_hex(8),
                "type": "payment.succeeded" if outcome == "success" else "payment.failed",
                "payment_id": payment_id,
                "order_id": payment["public_id"],
                "amount_kop": payment["total_kop"],
            }
        ).encode()
        _send_webhook(provider, body)
        return redirect(f"/order.html?id={payment['public_id']}")

    return bp


def _send_webhook(provider: FakePaymentProvider, body: bytes) -> None:
    """Как настоящий провайдер: подписывает тело и шлёт POST на webhook магазина."""
    timestamp = str(int(time.time()))
    request = urllib.request.Request(
        f"{provider.base_url}/webhooks/payment",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": provider.sign(timestamp, body),
        },
    )
    try:
        urllib.request.urlopen(request, timeout=10).close()
    except urllib.error.HTTPError as error:
        abort(502, f"Магазин отклонил webhook: {error.code} {error.read().decode(errors='replace')}")
    except urllib.error.URLError as error:
        abort(502, f"Не удалось доставить webhook на {provider.base_url} (проверьте BASE_URL): {error.reason}")
