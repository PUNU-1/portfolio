// Страница заказа: показывает статус и позволяет повторить оплату.

const STATUS_TEXT = {
  created: "Создан, ждёт оплаты",
  paid: "Оплачен (тестовая оплата)",
  failed: "Ошибка оплаты",
};

const money = (kop) =>
  (kop / 100).toLocaleString("ru-RU", { minimumFractionDigits: 0, maximumFractionDigits: 2 }) + " ₽";

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  node.append(...children);
  return node;
}

const box = document.getElementById("order");
const orderId = new URLSearchParams(location.search).get("id");
let pollsLeft = 10;

async function retryPayment() {
  const response = await fetch(`/api/orders/${encodeURIComponent(orderId)}/pay`, { method: "POST" });
  const data = await response.json();
  if (response.ok) window.location.href = data.payment_url;
  else alert(data.error || "Не удалось начать оплату");
}

function render(order) {
  const children = [
    el("span", { className: `status ${order.status}`, textContent: STATUS_TEXT[order.status] || order.status }),
    el("p", { className: "muted small", textContent: `Номер заказа: ${order.public_id}` }),
    el(
      "ul",
      { className: "order-lines" },
      ...order.items.map((item) =>
        el("li", {}, el("span", { textContent: `${item.title} × ${item.qty}` }), el("span", { textContent: money(item.price_kop * item.qty) }))
      )
    ),
    el("p", { className: "big", textContent: money(order.total_kop) }),
  ];

  if (order.status === "failed") {
    children.push(el("p", { className: "muted", textContent: "Банк отклонил платёж. Можно попробовать ещё раз." }));
  }
  if (order.status !== "paid") {
    const label = order.status === "failed" ? "Попробовать оплатить снова" : "Перейти к оплате";
    children.push(el("div", { className: "row" }, el("button", { className: "btn primary", type: "button", textContent: label, onclick: retryPayment })));
  }
  box.replaceChildren(...children);
}

async function load() {
  if (!orderId) {
    box.textContent = "Не указан номер заказа.";
    return;
  }
  const response = await fetch(`/api/orders/${encodeURIComponent(orderId)}`);
  if (!response.ok) {
    box.textContent = "Заказ не найден.";
    return;
  }
  const { order } = await response.json();
  render(order);

  // Webhook мог ещё не дойти — несколько раз перепроверяем статус
  if (order.status === "created" && pollsLeft-- > 0) setTimeout(load, 3000);
}

load();
