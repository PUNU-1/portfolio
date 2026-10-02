// Каталог, корзина и оформление заказа. Корзина живёт в localStorage браузера.
// Цены на сервере пересчитываются заново, поэтому подменить цену в браузере нельзя.

const CART_KEY = "demo_shop_cart";

const money = (kop) =>
  (kop / 100).toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + " ₽";

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children);
  return node;
}

let products = [];
let cart = loadCart(); // { "tee": 2, "mug": 1 }

function loadCart() {
  try {
    const parsed = JSON.parse(localStorage.getItem(CART_KEY));
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function saveCart() {
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  } catch {
    /* хранилище недоступно (приватный режим) — корзина просто не переживёт перезагрузку */
  }
}

function changeQty(id, delta) {
  const next = (cart[id] || 0) + delta;
  if (next <= 0) delete cart[id];
  else cart[id] = Math.min(next, 10);
  saveCart();
  renderCart();
}

function renderProducts() {
  const box = document.getElementById("products");
  box.replaceChildren(
    ...products.map((p) =>
      el(
        "article",
        { className: "card product" },
        el("img", { src: p.image, alt: p.title, width: 400, height: 300 }),
        el(
          "div",
          { className: "body" },
          el("h3", { textContent: p.title }),
          el("p", { textContent: p.description }),
          el("span", { className: "price", textContent: money(p.price_kop) }),
          el("button", { className: "btn", type: "button", textContent: "В корзину", onclick: () => changeQty(p.id, 1) })
        )
      )
    )
  );
}

function renderCart() {
  const list = document.getElementById("cart-items");
  const entries = Object.entries(cart).filter(([id]) => products.some((p) => p.id === id));

  list.replaceChildren(
    ...entries.map(([id, qty]) => {
      const product = products.find((p) => p.id === id);
      return el(
        "li",
        {},
        el("span", { textContent: product.title }),
        el("strong", { textContent: money(product.price_kop * qty) }),
        el(
          "span",
          { className: "qty" },
          el("button", { type: "button", textContent: "−", ariaLabel: "Меньше", onclick: () => changeQty(id, -1) }),
          el("span", { textContent: String(qty) }),
          el("button", { type: "button", textContent: "+", ariaLabel: "Больше", onclick: () => changeQty(id, 1) })
        )
      );
    })
  );

  const total = entries.reduce((sum, [id, qty]) => sum + products.find((p) => p.id === id).price_kop * qty, 0);
  document.getElementById("cart-total").textContent = money(total);
  document.getElementById("cart-empty").hidden = entries.length > 0;
  document.getElementById("checkout").hidden = entries.length === 0;
}

async function checkout(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector("button[type=submit]");
  const errorBox = document.getElementById("checkout-error");
  errorBox.textContent = "";
  button.disabled = true;

  const items = Object.entries(cart).map(([id, qty]) => ({ id, qty }));
  const customer = { name: form.elements.name.value, email: form.elements.email.value };

  try {
    const response = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, customer }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Не удалось оформить заказ");

    cart = {};
    saveCart();
    window.location.href = data.payment_url; // на страницу оплаты (сейчас — имитация банка)
  } catch (error) {
    errorBox.textContent = error.message;
    button.disabled = false;
  }
}

async function init() {
  const box = document.getElementById("products");
  try {
    const response = await fetch("/api/products");
    products = (await response.json()).products;
  } catch {
    box.textContent = "Не удалось загрузить каталог. Запущен ли сервер?";
    return;
  }
  renderProducts();
  renderCart();
  document.getElementById("checkout").addEventListener("submit", checkout);
}

init();
