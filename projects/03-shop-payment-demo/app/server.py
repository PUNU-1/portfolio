"""Flask-сервер: каталог, заказы, webhook. Запуск: python -m app.server"""
import logging

from flask import Flask, g, jsonify, request

from . import catalog, orders
from .config import BASE_DIR, Config, load_config
from .db import connect, init_db
from .payments import InvalidWebhook, get_provider
from .payments.fake import FakePaymentProvider
from .payments.fake_gateway import make_blueprint

log = logging.getLogger(__name__)


def create_app(config: Config | None = None) -> Flask:
    config = config or load_config()
    init_db(config.db_path)
    provider = get_provider(config)

    # static_url_path="" — файлы из static/ доступны с корня: /index.html, /order.html, /img/...
    app = Flask(
        __name__,
        static_folder=str(BASE_DIR / "static"),
        static_url_path="",
        template_folder=str(BASE_DIR / "templates"),
    )
    app.config["SHOP_CONFIG"] = config

    def get_db():
        if "db" not in g:
            g.db = connect(config.db_path)
        return g.db

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    if isinstance(provider, FakePaymentProvider):
        app.register_blueprint(make_blueprint(provider, get_db))

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    # ---------- API для сайта ----------

    @app.get("/api/products")
    def api_products():
        return jsonify(products=[catalog.to_public(p) for p in catalog.PRODUCTS])

    @app.post("/api/orders")
    def api_create_order():
        data = request.get_json(silent=True) or {}
        db = get_db()
        try:
            order = orders.create_order(db, data.get("items"), data.get("customer"))
        except orders.ValidationError as error:
            return jsonify(error=str(error)), 400

        session = _start_payment(db, order)
        return jsonify(order=orders.public_view(order), payment_url=session.payment_url), 201

    @app.get("/api/orders/<public_id>")
    def api_get_order(public_id: str):
        order = orders.get_order(get_db(), public_id)
        if order is None:
            return jsonify(error="Заказ не найден"), 404
        return jsonify(order=orders.public_view(order))

    @app.post("/api/orders/<public_id>/pay")
    def api_retry_payment(public_id: str):
        """Новая попытка оплаты (например, после ошибки)."""
        db = get_db()
        order = orders.get_order(db, public_id)
        if order is None:
            return jsonify(error="Заказ не найден"), 404
        if order["status"] == orders.PAID:
            return jsonify(error="Заказ уже оплачен"), 409
        session = _start_payment(db, order)
        return jsonify(payment_url=session.payment_url)

    def _start_payment(db, order: dict):
        session = provider.create_payment(
            order_public_id=order["public_id"],
            amount_kop=order["total_kop"],
            description=f"Заказ {order['public_id']}",
            return_url=f"{config.base_url}/order.html?id={order['public_id']}",
        )
        orders.add_payment(db, order, provider.name, session.payment_id)
        return session

    # ---------- webhook от платёжной системы ----------

    @app.post("/webhooks/payment")
    def payment_webhook():
        # 1) проверяем подлинность по сырому телу запроса; 2) только потом доверяем содержимому
        try:
            event = provider.parse_webhook(request.headers, request.get_data())
        except InvalidWebhook as error:
            log.warning("Webhook отклонён: %s", error)
            return jsonify(error="invalid webhook"), 400

        try:
            result = orders.apply_event(get_db(), event)
        except orders.EventRejected as error:
            log.warning("Webhook %s не применён: %s", event.event_id, error)
            return jsonify(error=str(error)), 422

        log.info("Webhook %s обработан: %s", event.event_id, result)
        return jsonify(result=result)

    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config()
    app = create_app(config)
    if config.secret_was_generated:
        log.info("PAYMENT_WEBHOOK_SECRET не задан: на время работы создан случайный секрет (для заглушки этого достаточно).")
    log.info("Демо-магазин: %s  (реальные платежи не проходят). Остановить: Ctrl+C", config.base_url)
    app.run(host="127.0.0.1", port=config.port, threaded=True)


if __name__ == "__main__":
    main()
