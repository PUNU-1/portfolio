// Подставляет в страницу данные из site.config.js: имя, контакты, ссылки на проекты, цены, форма.
(function () {
  "use strict";

  var cfg = window.SITE_CONFIG;
  if (!cfg) return;

  var person = cfg.person || {};
  var contacts = cfg.contacts || {};
  var $ = function (selector) { return document.querySelector(selector); };
  var $$ = function (selector) { return Array.prototype.slice.call(document.querySelectorAll(selector)); };

  function h(tag, props) {
    var node = document.createElement(tag);
    Object.assign(node, props || {});
    for (var i = 2; i < arguments.length; i++) { if (arguments[i]) node.append(arguments[i]); }
    return node;
  }

  function tgName(handle) { return String(handle || "").replace(/^@/, "").replace(/^https?:\/\/t\.me\//, ""); }
  var telegram = tgName(contacts.telegram);

  // ---------- Имя, SEO, плашка-напоминание ----------

  $$("[data-person-name]").forEach(function (node) { node.textContent = person.name || ""; });

  var title = (person.name || "") + ": " + (person.role || "");
  if (person.name) {
    document.title = title;
    var ogTitle = $('meta[property="og:title"]');
    if (ogTitle) ogTitle.setAttribute("content", title);
  }

  var seo = cfg.seo || {};
  if (seo.url) document.head.append(h("link", { rel: "canonical", href: seo.url }));

  var sameAs = [contacts.github, telegram ? "https://t.me/" + telegram : ""].filter(Boolean);
  var ld = h("script", { type: "application/ld+json" });
  ld.textContent = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "Person",
    name: person.name,
    jobTitle: person.role,
    url: seo.url || undefined,
    sameAs: sameAs,
  });
  document.head.append(ld);

  // Пока в конфиге заглушки, показываем плашку: чтобы случайно не выложить сайт с чужим @your_telegram
  var isTemplate = person.name === "Твоё Имя" || contacts.telegram === "@your_telegram" || /your-username/.test(contacts.github || "");
  $("#setup-notice").hidden = !isTemplate;

  if (person.photo) {
    var photo = $("#photo");
    photo.src = person.photo;
    photo.alt = person.name ? "Фото: " + person.name : "";
    photo.hidden = false;
  }

  $("#year").textContent = new Date().getFullYear();

  // ---------- Контакты ----------

  $$("[data-telegram-link]").forEach(function (link) {
    if (!telegram) return;
    link.href = "https://t.me/" + telegram;
    link.target = "_blank";
    link.rel = "noopener";
  });
  $$("[data-telegram-text]").forEach(function (link) { link.textContent = telegram ? "@" + telegram : ""; });

  if (contacts.email) {
    var emailItem = $("#contact-email");
    var emailLink = emailItem.querySelector("a");
    emailLink.href = "mailto:" + contacts.email;
    emailLink.textContent = contacts.email;
    emailItem.hidden = false;
  }
  if (contacts.github) {
    var githubItem = $("#contact-github");
    var githubLink = githubItem.querySelector("a");
    githubLink.href = contacts.github;
    githubLink.textContent = contacts.github.replace(/^https?:\/\/(www\.)?/, "");
    githubItem.hidden = false;
  }

  // ---------- Ссылки проектов: пустая ссылка — кнопка скрыта, а не «битая» ----------

  var projects = cfg.projects || {};
  $$("[data-project-code]").forEach(function (link) {
    var url = (projects[link.dataset.projectCode] || {}).code;
    if (url) link.href = url; else link.hidden = true;
  });
  $$("[data-project-demo]").forEach(function (link) {
    var url = (projects[link.dataset.projectDemo] || {}).demo;
    if (url) { link.href = url; link.hidden = false; } else link.hidden = true;
  });

  // ---------- Услуги и цены ----------

  $("#services-note").textContent = cfg.servicesNote || "";
  var list = $("#services-list");
  (cfg.services || []).forEach(function (service) {
    list.append(h("li", {},
      h("div", {}, h("h3", { textContent: service.title }), h("p", { textContent: service.text })),
      h("div", { className: "service-price", textContent: service.price },
        service.term ? h("span", { className: "service-term", textContent: service.term }) : null)
    ));
  });

  // ---------- Тема и меню ----------

  var root = document.documentElement;
  var themeButton = $("#theme-toggle");
  function syncTheme() { themeButton.setAttribute("aria-pressed", String(root.getAttribute("data-theme") === "dark")); }
  syncTheme();
  themeButton.addEventListener("click", function () {
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("theme", next); } catch (e) { /* приватный режим */ }
    syncTheme();
  });

  var menuButton = $("#menu-toggle");
  var nav = $("#nav");
  function closeMenu() { nav.classList.remove("is-open"); menuButton.setAttribute("aria-expanded", "false"); }
  menuButton.addEventListener("click", function () {
    var open = nav.classList.toggle("is-open");
    menuButton.setAttribute("aria-expanded", String(open));
  });
  nav.addEventListener("click", function (event) { if (event.target.tagName === "A") closeMenu(); });
  document.addEventListener("keydown", function (event) { if (event.key === "Escape") closeMenu(); });

  // ---------- Форма заявки ----------

  var f = cfg.form || {};
  var form = $("#lead-form");
  var status = $("#form-status");
  var submit = form.querySelector("button[type=submit]");

  function show(message, kind) {
    status.textContent = message;
    status.className = "form-status" + (kind ? " is-" + kind : "");
  }

  function invalid(field, message) {
    field.setAttribute("aria-invalid", "true");
    show(message, "error");
    field.focus();
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (form.elements.website.value) return; // скрытое поле заполнил бот

    var name = form.elements.name.value.trim();
    var contact = form.elements.contact.value.trim();
    var task = form.elements.task.value.trim();
    ["name", "contact", "task"].forEach(function (key) { form.elements[key].removeAttribute("aria-invalid"); });

    if (name.length < 2) return invalid(form.elements.name, "Подскажите, как к вам обращаться.");
    if (contact.length < 3) return invalid(form.elements.contact, "Оставьте контакт, чтобы я мог ответить.");
    if (task.length < 10) return invalid(form.elements.task, "Опишите задачу хотя бы парой предложений.");
    if (!form.elements.consent.checked) { show("Нужно согласие на обработку данных.", "error"); form.elements.consent.focus(); return; }

    send({ name: name, contact: contact, task: task, budget: form.elements.budget.value });
  });

  function send(lead) {
    if (f.endpoint) {
      submit.disabled = true;
      show("Отправляем…");
      fetch(f.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(Object.assign({}, f.extraFields, lead)),
      }).then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        form.reset();
        show("Спасибо! Заявка отправлена, отвечу в Telegram или по указанному контакту.", "ok");
      }).catch(function () {
        show("Не получилось отправить." + (telegram ? " Напишите мне в Telegram: @" + telegram : " Попробуйте позже."), "error");
      }).finally(function () { submit.disabled = false; });
      return;
    }

    if (f.telegramFallback && telegram) {
      if (contacts.telegram === "@your_telegram") {
        // Заглушку не открываем: по ней можно попасть в чужой профиль
        show("Контакт ещё не настроен: впишите свой Telegram в site.config.js (раздел contacts).", "error");
        return;
      }
      var text = "Заявка с сайта\nИмя: " + lead.name + "\nКонтакт: " + lead.contact + "\nЗадача: " + lead.task +
        (lead.budget ? "\nБюджет: " + lead.budget : "");
      window.open("https://t.me/" + telegram + "?text=" + encodeURIComponent(text), "_blank", "noopener");
      show("Открылся Telegram с готовым сообщением. Нажмите «Отправить» там, чтобы оно дошло.", "ok");
      return;
    }

    show("Демо-режим: форма пока никуда не отправляет. Подключите отправку в site.config.js (раздел form).", "ok");
  }
})();
