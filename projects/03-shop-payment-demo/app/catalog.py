"""Каталог: три тестовых товара. Цены хранятся в копейках, чтобы не путаться с дробными числами."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    description: str
    price_kop: int
    image: str


PRODUCTS = (
    Product("tee", "Футболка «Демо»", "Тестовый товар: хлопок, один размер на всех. Не существует.", 199000, "/img/tee.svg"),
    Product("mug", "Кружка «Демо»", "Тестовый товар: керамика, 330 мл. Не существует.", 79000, "/img/mug.svg"),
    Product("stickers", "Набор стикеров «Демо»", "Тестовый товар: десять наклеек. Не существует.", 29000, "/img/stickers.svg"),
)


def find(product_id: str) -> Product | None:
    for product in PRODUCTS:
        if product.id == product_id:
            return product
    return None


def to_public(product: Product) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "description": product.description,
        "price_kop": product.price_kop,
        "image": product.image,
    }
