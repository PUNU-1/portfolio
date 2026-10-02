// Собирает страницу из site.config.js. Править этот файл не нужно: все тексты и настройки — в конфиге.
(function () {
  "use strict";

  var cfg = window.SITE_CONFIG;
  if (!cfg) {
    document.body.textContent = "Не найден site.config.js";
    return;
  }

  var $ = function (selector) { return document.querySelector(selector); };

  // Создаёт элемент: h("a", { href: "#", textContent: "Ссылка" }, дочерние...)
  function h(tag, props) {
    var node = document.createElement(tag);
    Object.assign(node, props || {});
    for (var i = 2; i < arguments.length; i++) {
      if (arguments[i]) node.append(arguments[i]);
    }
    return node;
  }

  function setText(selector, text) { var node = $(selector); if (node) node.textContent = text || ""; return node; }
  function digits(phone) { return String(phone || "").replace(/[^\d+]/g, ""); }
  function tgName(handle) { return String(handle || "").replace(/^@/, "").replace(/^https?:\/\/t\.me\//, ""); }

  // ---------- SEO: заголовок, описание, структурированные данные ----------

  function setMeta(selector, attr, value) {
    var node = $(selector);
    if (!node) return;
    node.setAttribute(attr, value);
  }

  function applySeo() {
    var seo = cfg.seo || {};
    if (seo.title) {
      document.title = seo.title;
      setMeta('meta[property="og:title"]', "content", seo.title);
    }
    if (seo.description) {
      setMeta('meta[name="description"]', "content", seo.description);
      setMeta('meta[property="og:description"]', "content", seo.description);
    }
    if (cfg.theme && cfg.theme.accent) setMeta('meta[name="theme-color"]', "content", cfg.theme.accent);

    if (seo.url) {
      document.head.append(h("link", { rel: "canonical", href: seo.url }));
      var ogUrl = h("meta", { content: seo.url });
      ogUrl.setAttribute("property", "og:url");
      document.head.append(ogUrl);
    }

    // Данные о бизнесе для поисковиков (schema.org). Добавляются только те поля, что заполнены.
    var contacts = cfg.contacts || {};
    var data = { "@context": "https://schema.org", "@type": "LocalBusiness", name: (cfg.brand || {}).name };
    if (contacts.phone) data.telephone = contacts.phone;
    if (contacts.email) data.email = contacts.email;
    if (contacts.address) data.address = { "@type": "PostalAddress", streetAddress: contacts.address };
    if (seo.url) data.url = seo.url;
    if (seo.description) data.description = seo.description;
    var script = h("script", { type: "application/ld+json" });
    script.textContent = JSON.stringify(data);
    document.head.append(script);
  }

  // ---------- Шапка и навигация ----------

  function renderHeader() {
    var brand = cfg.brand || {};
    var link = $("#brand");
    if (brand.logoImage) {
      link.append(h("img", { src: brand.logoImage, alt: "", width: 36, height: 36 }));
    } else {
      link.append(h("span", { className: "brand-mark", textContent: (brand.name || "?").charAt(0).toUpperCase() }));
    }
    link.append(h("span", { textContent: brand.name || "" }));
    if (brand.tagline) link.append(h("small", { textContent: brand.tagline }));

    var items = [
      ["#services", "Услуги", cfg.services && cfg.services.length],
      ["#prices", "Цены", cfg.prices && cfg.prices.length],
      ["#faq", "Вопросы", cfg.faq && cfg.faq.length],
      ["#contacts", "Контакты", true],
    ];
    var nav = $("#nav");
    items.forEach(function (item) {
      if (item[2]) nav.append(h("a", { href: item[0], textContent: item[1] }));
    });

    var phone = (cfg.contacts || {}).phone;
    if (phone) {
      var phoneLink = $("#header-phone");
      phoneLink.href = "tel:" + digits(phone);
      phoneLink.textContent = phone;
      phoneLink.hidden = false;
    }

    if (cfg.demoNotice) {
      var notice = $("#demo-notice");
      notice.textContent = cfg.demoNotice;
      notice.hidden = false;
    }
  }

  // ---------- Содержимое секций ----------

  function renderHero() {
    var hero = cfg.hero || {};
    setText("#hero-title", hero.title);
    setText("#hero-subtitle", hero.subtitle);
    setText("#hero-primary", hero.primaryButton || "Записаться");

    var phone = (cfg.contacts || {}).phone;
    if (phone && hero.secondaryButton) {
      var secondary = $("#hero-secondary");
      secondary.textContent = hero.secondaryButton;
      secondary.href = "tel:" + digits(phone);
      secondary.hidden = false;
    }

    // Иллюстрация справа: "pole" (полосатый шест, по умолчанию), "none" или путь к своей картинке
    var art = hero.art || "pole";
    var artBox = $(".hero-art");
    if (art === "none") {
      artBox.remove();
    } else if (art !== "pole") {
      artBox.replaceChildren(h("img", { src: art, alt: "", width: 360, height: 360, className: "hero-img" }));
    }

    var facts = $("#hero-facts");
    (hero.facts || []).forEach(function (fact) { facts.append(h("li", { textContent: fact })); });
  }

  function renderServices() {
    var list = cfg.services || [];

    // список услуг в форме заявки
    var select = $("#form-service");
    select.append(h("option", { value: "", textContent: "Не выбрано" }));
    list.forEach(function (service) { select.append(h("option", { value: service.title, textContent: service.title })); });

    var section = $("#services");
    if (!list.length) { section.remove(); return; }
    setText("#services-title", cfg.servicesTitle || "Услуги");
    var box = $("#services-list");
    list.forEach(function (service) {
      box.append(h("article", { className: "card" },
        h("h3", { textContent: service.title }),
        h("p", { textContent: service.text }),
        service.duration ? h("p", { className: "duration", textContent: service.duration }) : null
      ));
    });
  }

  function renderPrices() {
    var list = cfg.prices || [];
    var section = $("#prices");
    if (!list.length) { section.remove(); return; }
    setText("#prices-title", cfg.pricesTitle || "Цены");
    var body = $("#prices-body");
    list.forEach(function (row) {
      body.append(h("tr", {}, h("td", { textContent: row.name }), h("td", { textContent: row.price })));
    });
    setText("#prices-note", cfg.pricesNote);
  }

  function renderFaq() {
    var list = cfg.faq || [];
    var section = $("#faq");
    if (!list.length) { section.remove(); return; }
    setText("#faq-title", cfg.faqTitle || "Частые вопросы");
    var box = $("#faq-list");
    list.forEach(function (item) {
      box.append(h("details", {}, h("summary", { textContent: item.q }), h("p", { textContent: item.a })));
    });
  }

  function renderContacts() {
    var c = cfg.contacts || {};
    setText("#contacts-title", cfg.contactsTitle || "Контакты");

    var dl = h("dl");
    function row(title, content) {
      if (!content) return;
      dl.append(h("div", {}, h("dt", { textContent: title }), h("dd", {}, content)));
    }

    row("Телефон", c.phone && h("a", { href: "tel:" + digits(c.phone), textContent: c.phone }));
    row("Telegram", c.telegram && h("a", { href: "https://t.me/" + tgName(c.telegram), textContent: "@" + tgName(c.telegram), target: "_blank", rel: "noopener" }));
    row("Email", c.email && h("a", { href: "mailto:" + c.email, textContent: c.email }));

    if (c.address) {
      var address = h("span", { textContent: c.address });
      if (c.mapUrl) {
        address = h("span", {}, c.address + " ", h("a", { href: c.mapUrl, textContent: "На карте", target: "_blank", rel: "noopener" }));
      }
      row("Адрес", address);
    }
    if ((c.hours || []).length) {
      var hours = h("ul", { className: "hours" });
      c.hours.forEach(function (item) { hours.append(h("li", { textContent: item.days + ": " + item.time })); });
      row("Часы работы", hours);
    }
    $("#contacts-info").append(dl);
  }

  function renderFooter() {
    var footer = cfg.footer || {};
    setText("#footer-text", footer.text);
    var privacy = (cfg.form || {}).privacyUrl;
    if (privacy) {
      var link = $("#footer-privacy");
      link.href = privacy;
      link.hidden = false;
    }
  }

  // ---------- Тема и мобильное меню ----------

  function setupTheme() {
    var button = $("#theme-toggle");
    var root = document.documentElement;
    function sync() { button.setAttribute("aria-pressed", String(root.getAttribute("data-theme") === "dark")); }
    sync();
    button.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) { /* приватный режим — просто не запоминаем */ }
      sync();
    });
  }

  function setupMenu() {
    var button = $("#menu-toggle");
    var nav = $("#nav");
    function close() { nav.classList.remove("is-open"); button.setAttribute("aria-expanded", "false"); }
    button.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      button.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", function (event) { if (event.target.tagName === "A") close(); });
    document.addEventListener("keydown", function (event) { if (event.key === "Escape") close(); });
  }

  // ---------- Форма заявки ----------

  function setupForm() {
    var f = cfg.form || {};
    var form = $("#lead-form");
    var status = $("#form-status");
    var submit = $("#form-submit");

    setText("#form-title", f.title || "Оставить заявку");
    setText("#form-subtitle", f.subtitle);
    submit.textContent = f.submitText || "Отправить";
    setText("#form-consent", f.consentText || "Я согласен(на) на обработку персональных данных");
    var consent = $("#form-consent");
    if (f.privacyUrl) consent.append(" (", h("a", { href: f.privacyUrl, textContent: "политика", target: "_blank", rel: "noopener" }), ")");

    function show(message, kind) {
      status.textContent = message;
      status.className = "form-status" + (kind ? " is-" + kind : "");
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (form.elements.website.value) return; // заполнил скрытое поле — это бот

      var name = form.elements.name.value.trim();
      var phone = form.elements.phone.value.trim();
      form.elements.name.setAttribute("aria-invalid", String(name.length < 2));
      form.elements.phone.setAttribute("aria-invalid", String(phone.replace(/\D/g, "").length < 6));
      if (name.length < 2) { show("Укажите имя.", "error"); form.elements.name.focus(); return; }
      if (phone.replace(/\D/g, "").length < 6) { show("Укажите телефон, чтобы мы могли связаться.", "error"); form.elements.phone.focus(); return; }
      if (!form.elements.consent.checked) { show("Нужно согласие на обработку данных.", "error"); form.elements.consent.focus(); return; }

      var lead = {
        name: name,
        phone: phone,
        service: form.elements.service.value,
        comment: form.elements.comment.value.trim(),
      };
      send(lead);
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
          show("Спасибо! Заявка отправлена, мы скоро свяжемся с вами.", "ok");
        }).catch(function () {
          var phone = (cfg.contacts || {}).phone;
          show("Не получилось отправить заявку." + (phone ? " Позвоните нам: " + phone : " Попробуйте позже."), "error");
        }).finally(function () { submit.disabled = false; });
        return;
      }

      var telegram = tgName((cfg.contacts || {}).telegram);
      if (f.telegramFallback && telegram) {
        var text = "Заявка с сайта\nИмя: " + lead.name + "\nТелефон: " + lead.phone +
          (lead.service ? "\nУслуга: " + lead.service : "") + (lead.comment ? "\nКомментарий: " + lead.comment : "");
        window.open("https://t.me/" + telegram + "?text=" + encodeURIComponent(text), "_blank", "noopener");
        show("Открылся Telegram с готовым сообщением. Нажмите «Отправить», чтобы заявка дошла.", "ok");
        return;
      }

      show("Демо-режим: заявка никуда не отправлена. Подключите отправку в site.config.js (раздел form).", "ok");
    }
  }

  // ---------- Запуск ----------

  applySeo();
  renderHeader();
  renderHero();
  renderServices();
  renderPrices();
  renderFaq();
  renderContacts();
  renderFooter();
  setupTheme();
  setupMenu();
  setupForm();
})();
