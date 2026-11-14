<h1 align="center">eShop</h1>

<p align="center">
  A full-stack online store built with Flask: browse, search, review and order products, with an admin panel for the shop owner.
</p>

<p align="center">
  <a href="#features">Features</a>
  ·
  <a href="#getting-started">Getting started</a>
  ·
  <a href="#security">Security</a>
  ·
  <a href="flask_eshop/DEPLOY.md">Deployment</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white">
  <img alt="JavaScript" src="https://img.shields.io/badge/JavaScript-vanilla-F7DF1E?logo=javascript&logoColor=black">
  <img alt="Languages" src="https://img.shields.io/badge/languages-English_%7C_Ελληνικά-0A66C2">
</p>

<!-- Screenshots: add images to docs/screenshots/ and uncomment.
<p align="center">
  <img src="docs/screenshots/shop.png" alt="Shop page with filters and product grid" width="62%">
  <img src="docs/screenshots/mobile.png" alt="Product page on mobile" width="24%">
</p>
-->

## Overview

eShop is a complete store, from the product grid to the order history. Customers can search the catalogue, filter and sort it, save items for later, leave reviews, and check out. Stock is updated safely, even when two people order at once. The shop owner manages products, images and orders from an admin panel.

The server is Flask with plain SQL on SQLite, and the front end uses vanilla JavaScript, with no frontend framework. The whole site is available in English and Greek, and the store ships with about 60 sample products, so it looks real from the first run.

## Features

**Shopping**
- A product grid with pagination, filters for category, price range and stock, and sorting by newest, price, name or rating.
- Filters update the results without reloading the page, and the active filters appear as removable chips.
- Live search suggestions while typing. The search ignores accents, so a search for *καφες* finds *Καφές*.
- Product pages with images, stock status and star ratings.
- A wishlist (*Saved items*) and *Recently viewed*, both kept in the browser.

**Cart and checkout**
- A slide-out cart drawer, plus a full cart page where you can change quantities. Quantities can never go above the stock.
- Free shipping over €50, otherwise a €9.99 shipping fee, plus 8% tax, shown before you pay.
- A two-step checkout with shipping details and a payment method. Payment is simulated, so no real charges are made.
- Orders run in a single database transaction. The app checks and reduces stock together, so two customers can never buy the last item.

**Accounts and reviews**
- Customers can register and log in. Passwords are hashed with bcrypt, and too many failed logins are rate-limited.
- Each customer has an order history with the items and the status of every order.
- Customers can give star ratings and reviews. Average ratings appear on product cards and can be used for sorting.

**Admin panel** (`/admin`)
- Add, edit and delete products, each with a Greek and an English name and description.
- Upload a product image or fetch one from a URL. Thumbnails are created automatically.
- Manage orders through *pending → paid → shipped*, or cancel them. Cancelling an order puts its items back in stock.

**Everywhere**
- English and Greek, chosen from a menu or detected from the browser. Both the server-rendered pages and the JavaScript are translated.
- A responsive layout for desktop and mobile, with toast notifications and friendly 404 and 500 pages.

## Tech stack

| Area       | Choice                                                                 |
| ---------- | ---------------------------------------------------------------------- |
| Backend    | Python and Flask 3, using the app factory pattern with one blueprint per area |
| Database   | SQLite with hand-written, parameterised SQL                            |
| Templates  | Jinja2 with shared partials and macros                                 |
| Frontend   | Vanilla JavaScript (fetch/AJAX) and modular CSS, one file per page     |
| Security   | Flask-WTF (CSRF), bcrypt, security headers                             |
| Images     | Pillow, for validation and thumbnails                                  |
| i18n       | A small custom translation layer, with JSON catalogues shared with the JavaScript |
| Serving    | Waitress (Windows), Gunicorn (Linux), Cloudflare Tunnel for public demos |

## Architecture

```
flask_eshop/
├── run.py              # entry point
└── eshop/
    ├── __init__.py     # create_app(): config, CSRF, blueprints, error handlers
    ├── db.py           # schema, sample data, CLI commands
    ├── security.py     # password hashing, rate limiting, login/admin decorators
    ├── images.py       # uploads, safe URL downloads, thumbnails
    ├── i18n.py         # English/Greek translations
    ├── routes/         # main, api, auth, cart, orders, reviews, admin
    ├── templates/      # one folder per area, plus shared partials
    └── static/         # CSS and JS, one file per page
```

- **App factory and blueprints.** `create_app()` builds the app, so tests and the deployment can create their own instance. Each part of the site is a separate blueprint.
- **The database has five tables:** `users`, `products`, `orders`, `order_items` and `reviews`. Each order item stores the price at the time of purchase, so later price changes don't rewrite old orders.
- **Pages render on the server.** Filtering, search suggestions, the cart drawer and admin actions then fetch only what changed, as HTML fragments or JSON.

## Security

- **CSRF:** every form and AJAX request carries a token (Flask-WTF).
- **Passwords:** hashed with bcrypt. Login is limited to 5 attempts every 15 minutes. The first admin password comes from `.env`, or is generated randomly and printed once.
- **SQL injection:** all queries use parameters, sort options come from a fixed list, and `LIKE` wildcards in searches are escaped.
- **Sessions:** cookies are `SameSite=Lax`, and `Secure` when the site runs over HTTPS. The secret key comes from `.env`, or is generated once per install.
- **Open redirects:** after login, the app only returns you to pages on the same site.
- **SSRF:** *Image from URL* downloads only from public internet addresses. Private networks and localhost are refused, even through redirects. Only images are accepted, up to 16 MB and with a 10-second timeout.
- **Headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` and a strict `Referrer-Policy`.
- **Admin routes:** protected by role checks on the server, not just hidden in the interface.

## Getting started

### Quick start (Windows)

Double-click **`flask_eshop/start.bat`**. It checks for Python 3.10+, creates a virtual environment, installs the dependencies, and asks whether to run the shop:
- **Locally**, at http://localhost:8000, or
- **Publicly**, through a free temporary Cloudflare HTTPS address you can send to anyone. cloudflared is installed automatically if it's missing.

### Manual setup

```bash
git clone https://github.com/Christos2424/eshop-project.git
cd eshop-project/flask_eshop

python -m venv venv
venv\Scripts\Activate.ps1        # Windows (PowerShell)
source venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
python run.py                    # or: flask --app eshop run --debug
```

### Admin account

On the first run the app creates an admin account (`admin@eshop.com`). To choose its password, copy `.env.example` to `.env` and set `ADMIN_PASSWORD` (and optionally `ADMIN_EMAIL`) before starting. Otherwise a random password is printed in the terminal.

| Command                                        | What it does                                          |
| ---------------------------------------------- | ----------------------------------------------------- |
| `flask --app eshop init-db`                    | Creates the tables and the admin account              |
| `flask --app eshop seed-products`              | Adds the sample products                              |
| `flask --app eshop set-password <email>`       | Changes a user's password                             |

## Deployment

The shop can be hosted for free on **PythonAnywhere**, or on any VPS with Gunicorn behind Nginx or Caddy. Step-by-step instructions are in [`DEPLOY.md`](flask_eshop/DEPLOY.md).

## Roadmap

- Automated tests (pytest) and CI
- Real payments through a provider's test mode, such as Stripe
- Order confirmation emails
- Product variants (size and colour)
