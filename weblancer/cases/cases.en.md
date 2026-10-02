# Portfolio cases for Weblancer (English)

Six cases. For each: title, category, ready-to-paste description, images and links.

**Links.** Already filled in: GitHub `PUNU-1`, repository `portfolio`. Live demos will work at `https://punu-1.github.io/portfolio/demos/...` once the site is published (see the root README).

**Honesty rule.** Every case clearly says it is a demo project on a fictional company. Don't remove that label and never call these client work. No real clients or reviews yet is fine: the client can see working code.

Images are in `weblancer/images/`.

---

## Case 1. Telegram booking bot (demo project)

**Category:** Bots & automation / Python
**Images:** `bot-booking-1.png`, `bot-booking-2.png`
**Code:** `https://github.com/PUNU-1/portfolio/tree/main/projects/01-booking-bot`

**Description:**

> Demo project: a booking bot for a barbershop, salon or clinic. The business is fictional.
>
> **Problem.** Bookings happen in private messages: the receptionist gets interrupted, times get mixed up, two clients end up in the same slot.
>
> **What I built.** The client picks a service, date and free time, then confirms. Taken times are never shown and double booking is impossible (a database transaction check plus a unique index). The owner gets an instant notification about every new booking and cancellation. Clients get `/my_bookings` and `/cancel`; the admin gets `/today` with the day's bookings. Services, prices, working hours and days off are changed in one file, no code edits.
>
> **Verified.** 23 automated tests: free-slot logic, the database, two clients booking the same time at once, and the full dialog on a mocked Telegram. It has not been run in live Telegram with a real token in this build.
>
> **Stack.** Python, aiogram 3, SQLite, pytest.

---

## Case 2. AI assistant in Telegram answering from your FAQ (demo project)

**Category:** Bots / AI assistants
**Images:** `bot-assistant.png`
**Code:** `https://github.com/PUNU-1/portfolio/tree/main/projects/04-ai-assistant-bot`

**Description:**

> Demo project: a bot that answers customers from a company knowledge base kept in a plain text file.
>
> **Problem.** Customers keep asking the same questions (address, hours, prices, cancellations) and nobody answers at night.
>
> **What I built.** The bot finds the relevant FAQ passages and answers only from them. If the answer isn't there, it says so and points to a human operator instead of making things up. It remembers recent turns, limits messages per user per day, and clearly states it is an AI. The model, API URL and key are set in `.env`: any OpenAI-compatible API works. A no-model mode allows free testing.
>
> **Verified.** 29 automated tests (knowledge search, memory, rate limit, model failure, dialog). The API client was checked against a local fake server. The image shows the bot in no-model mode: replies are quotes from the knowledge base, while with a real model the wording is free-form. It has not been run with a real model and key in this build.
>
> **Stack.** Python, aiogram 3, OpenAI-compatible API, SQLite, pytest.

---

## Case 3. Landing page template for local businesses (demo project)

**Category:** Web design & front-end / Landing pages
**Images:** `landing-barber-desktop.png`, `landing-barber-mobile.png`
**Live demo:** `https://punu-1.github.io/portfolio/demos/landing/`
**Code:** `https://github.com/PUNU-1/portfolio/tree/main/projects/02-landing-template`

**Description:**

> Demo project: a responsive landing page template, shown with a fictional barbershop.
>
> **Problem.** A craftsperson or small company needs a one-page site: what they do, what it costs, how to book. No site builder and no month of waiting.
>
> **What I built.** Mobile and desktop layouts, light and dark themes, sections for services, prices, FAQ and contacts, and a lead form with spam-bot protection and a data-processing consent checkbox. SEO: headings, meta tags, Open Graph, structured data. Fast: about 40 KB with no frameworks or external fonts. It's a template: colors, copy, logo and hero illustration are changed in a single settings file.
>
> **Verified.** Checked in a browser on desktop and mobile, in both themes; the form was tested (validation, demo mode, submission to a test receiver).
>
> **Stack.** HTML, CSS, vanilla JavaScript.

---

## Case 4. Same template, different niche: a dental clinic (demo project)

**Category:** Web design & front-end / Landing pages
**Images:** `landing-dental-desktop.png`, `landing-dental-mobile.png`
**Live demo:** `https://punu-1.github.io/portfolio/demos/landing-dental/`
**Code:** `https://github.com/PUNU-1/portfolio/tree/main/projects/02-landing-template/examples/dental`

**Description:**

> Demo project: the landing template adapted to a fictional dental clinic, "Smile".
>
> **Why this case.** It shows how the template works: the code is identical; only the settings file, accent color, logo and hero illustration changed. For a client this means a fast, affordable adaptation to their niche.
>
> **What changed.** Copy, services, (example) prices, FAQ, opening hours, the brand color (light and dark variants), the logo and the hero illustration.
>
> **Stack.** HTML, CSS, vanilla JavaScript.

---

## Case 5. Design concept for an online-booking SaaS landing page, "Okoshko" (demo project)

**Category:** Web design / UI design
**Images:** `concept-desktop.png`, `concept-full.png`, `concept-mobile.png`
**Live demo:** `https://punu-1.github.io/portfolio/demos/saas-concept/`
**Code:** `https://github.com/PUNU-1/portfolio/tree/main/projects/05-saas-landing-concept`

**Description:**

> Design concept and build of a landing page for a fictional online-booking service for salons and freelancers. The service and all prices are made up.
>
> **Goal.** Show how I approach product landing page design, from idea and structure to a finished responsive build.
>
> **What I built.** A dark hero with a gradient background and one accent color; the product UI (day schedule and a booking notification) is built in pure CSS with no images; a bento grid of features, three steps, pricing with a highlighted plan, FAQ and a closing call to action. Responsive from phones to wide monitors, accessible (keyboard focus, contrast), respects `prefers-reduced-motion`.
>
> **Stack.** HTML, CSS (no frameworks, no external fonts).

---

## Case 6. Shop with a test payment step and a secure webhook (demo project)

**Category:** Web development / Payment integrations
**Images:** `shop-catalog.png`, `shop-gateway.png`, `shop-order-paid.png`
**Code:** `https://github.com/PUNU-1/portfolio/tree/main/projects/03-shop-payment-demo`

**Description:**

> Demo project: a three-product test shop with a cart, orders and a swappable payment layer. **No real payments are processed**, no money is charged, the products are fictional (stated on every page).
>
> **Problem.** Selling online takes more than a "Pay" button: you must know for certain whether an order is paid, and prevent forged payments or tampered prices.
>
> **What I built.** Catalog, cart, checkout, order statuses (created, paid, failed) and payment retry. The payment layer is an adapter: today it holds a "test payment" stub, and a real provider is plugged in by replacing one class (the README explains how). The webhook verifies an HMAC signature and request freshness, drops duplicate deliveries, and checks the amount and the payment-to-order link. Prices are computed on the server and order links can't be enumerated.
>
> **Verified.** 35 automated tests (signature, tampered body, stale request, replay, wrong amount, an end-to-end HTTP scenario). In a browser I walked the order, decline, retry, paid flow. Connecting a real payment provider was not tested in this build.
>
> **Stack.** Python, Flask, SQLite, JavaScript, pytest.

---

## Uploading the cases to Weblancer

1. Open the portfolio section of your profile and add an item.
2. Copy the title and description from here and take images from `weblancer/images/` (put the most striking one first: `concept-desktop.png` for case 5, `landing-barber-desktop.png` for case 3).
3. Use the live demo link if you have one; otherwise the GitHub code link.
4. Order: cases 5 and 3 first (visually strong), then 1 and 2 (bots), then 4 and 6.
5. Start titles with what the client sees: "Barbershop landing page…", "Telegram booking bot…". Keep the "demo project" label in the title or the first line of the description.
