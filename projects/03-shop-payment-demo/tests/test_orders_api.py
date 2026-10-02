import pytest


def test_catalog_has_three_products(client):
    products = client.get("/api/products").get_json()["products"]
    assert [p["id"] for p in products] == ["tee", "mug", "stickers"]


def test_order_total_is_calculated_on_server(shop, client):
    # клиент пытается подсунуть свою цену — сервер её игнорирует
    response = shop.order(items=[{"id": "tee", "qty": 1, "price_kop": 1}, {"id": "mug", "qty": 2, "price_kop": 1}])
    assert response.status_code == 201
    order = response.get_json()["order"]
    assert order["total_kop"] == 199000 + 2 * 79000
    assert order["status"] == "created"
    assert response.get_json()["payment_url"].startswith("http://127.0.0.1:5999/fake-gateway/fake_")


def test_order_status_endpoint_hides_email(shop, client):
    order = shop.order().get_json()["order"]
    data = client.get(f"/api/orders/{order['public_id']}").get_json()
    assert "email" not in str(data).lower()
    assert data["order"]["items"][0]["title"] == "Футболка «Демо»"


def test_unknown_order_is_404(client):
    assert client.get("/api/orders/nope").status_code == 404


@pytest.mark.parametrize(
    "items",
    [
        [],
        None,
        [{"id": "unknown", "qty": 1}],
        [{"id": "tee", "qty": 0}],
        [{"id": "tee", "qty": 11}],
        [{"id": "tee", "qty": "2"}],
        [{"id": "tee", "qty": True}],
        [{"id": "tee", "qty": 1}, {"id": "tee", "qty": 1}],
        ["tee"],
    ],
)
def test_bad_items_are_rejected(shop, items):
    response = shop.order(items=items)
    assert response.status_code == 400
    assert "error" in response.get_json()


@pytest.mark.parametrize("name,email", [("", "a@b.ru"), ("И", "a@b.ru"), ("Иван", "not-an-email"), ("Иван", "")])
def test_bad_customer_is_rejected(shop, name, email):
    assert shop.order(name=name, email=email).status_code == 400


def test_retry_payment_creates_new_payment(shop, client):
    order, first_payment = shop.order_with_payment()
    response = client.post(f"/api/orders/{order['public_id']}/pay")
    assert response.status_code == 200
    second_payment = response.get_json()["payment_url"].rsplit("/", 1)[-1]
    assert second_payment != first_payment
