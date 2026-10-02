"""Сквозной тест по настоящему HTTP: сервер в отдельном потоке, «банк» шлёт webhook сам себе."""
import json
import socket
import threading
import urllib.request

import pytest
from werkzeug.serving import make_server

from app.config import Config
from app.server import create_app


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def live_server(tmp_path):
    port = free_port()
    config = Config(
        db_path=str(tmp_path / "e2e.db"),
        port=port,
        base_url=f"http://127.0.0.1:{port}",
        provider="fake",
        webhook_secret="e2e-secret",
    )
    server = make_server("127.0.0.1", port, create_app(config), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield config.base_url
    server.shutdown()


def post_json(url, payload):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def get_json(url):
    with urllib.request.urlopen(url) as response:
        return json.load(response)


def click_gateway(base, payment_url, outcome):
    """Нажимает кнопку на странице «банка» (она шлёт подписанный webhook на сервер магазина)."""
    payment_id = payment_url.rsplit("/", 1)[-1]
    request = urllib.request.Request(f"{base}/fake-gateway/{payment_id}/{outcome}", method="POST")
    urllib.request.urlopen(request).close()


def test_full_purchase_over_http(live_server):
    base = live_server
    created = post_json(f"{base}/api/orders", {"items": [{"id": "stickers", "qty": 3}], "customer": {"name": "Тест", "email": "t@example.com"}})
    public_id = created["order"]["public_id"]
    assert get_json(f"{base}/api/orders/{public_id}")["order"]["status"] == "created"

    # страница «банка» открывается
    with urllib.request.urlopen(created["payment_url"]) as page:
        html = page.read().decode()
    assert "Тестовая оплата" in html and "реальные платежи не проходят" in html

    # неудачная попытка -> failed
    click_gateway(base, created["payment_url"], "fail")
    assert get_json(f"{base}/api/orders/{public_id}")["order"]["status"] == "failed"

    # повторная попытка -> paid
    retry = post_json(f"{base}/api/orders/{public_id}/pay", {})
    click_gateway(base, retry["payment_url"], "success")
    assert get_json(f"{base}/api/orders/{public_id}")["order"]["status"] == "paid"


def test_static_pages_are_served(live_server):
    for path, marker in [("/", "Демо-магазин"), ("/order.html", "Ваш заказ"), ("/img/mug.svg", "<svg")]:
        with urllib.request.urlopen(live_server + path) as response:
            assert marker in response.read().decode()
