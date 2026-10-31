Fixed console errors , fixed error handling ,added ico seperated the order handling for users and admins , changed products to be inspected when clicked uppon and fixed the order css .

## Project structure

```
flask_eshop/
├── run.py                   # Entry point: python run.py
├── requirements.txt
├── .env.example             # Optional settings (copy to .env)
├── instance/                # Local data, not in git (created automatically)
│   ├── eshop.db             # SQLite database
│   ├── secret_key           # Generated session key
│   └── uploads/             # Product images uploaded by admins
└── eshop/                   # Application package
    ├── __init__.py          # create_app(): app factory, CSRF, error handlers, template helpers
    ├── config.py            # Settings (upload limits, page size, ...)
    ├── db.py                # Connection handling, schema + sample data, CLI commands
    ├── security.py          # Password hashing, rate limiting, login/admin decorators
    ├── validators.py        # Form validation
    ├── images.py            # Product image upload / download
    ├── routes/              # One blueprint per area of the site
    │   ├── main.py          # Home, search, product page
    │   ├── auth.py          # Register, login, logout
    │   ├── cart.py          # Cart and checkout
    │   ├── orders.py        # Order history
    │   └── admin.py         # Product and order management (/admin/...)
    ├── templates/
    │   ├── base.html        # Page layout
    │   ├── partials/        # Header, footer, flash messages
    │   ├── shop/            # index, product
    │   ├── auth/            # login, register
    │   ├── cart/            # cart, checkout
    │   ├── orders/          # customer order history
    │   ├── admin/           # products, add/edit product, all orders
    │   └── errors/          # 404, 500
    └── static/
        ├── css/
        ├── images/
        └── js/              # base.js (every page) + one script per page
```

## Running

```powershell
cd flask_eshop
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Or with the Flask CLI: `flask --app eshop run --debug`.

## Admin account

On first run the app creates an admin account (`admin@eshop.com`) with a random
password and prints it in the terminal. To choose the password yourself, set
`ADMIN_PASSWORD` (and optionally `ADMIN_EMAIL`) in a `.env` file before the first run;
see `.env.example`.

To change any user's password later:

```powershell
flask --app eshop set-password admin@eshop.com
```

Other commands: `flask --app eshop init-db` creates the tables and sample data
without starting the server.

## Security

- All forms and AJAX requests are protected with CSRF tokens (Flask-WTF).
- The session key is read from `SECRET_KEY`, or generated once into `instance/secret_key`.
- After login, the `next` redirect only allows pages on this site.
- "Image from URL" only downloads from public internet addresses, accepts only
  images, and is limited to 16MB / 10 seconds.
