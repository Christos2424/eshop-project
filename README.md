Fixed console errors , fixed error handling ,added ico seperated the order handling for users and admins , changed products to be inspected when clicked uppon and fixed the order css .

## Project structure

```
flask_eshop/
├── run.py                 # Entry point: python run.py
├── requirements.txt
├── instance/
│   └── eshop.db           # SQLite database (created automatically)
└── eshop/                 # Application package
    ├── __init__.py        # create_app(): app factory, error handlers, template helpers
    ├── config.py          # Settings (secret key, upload limits, page size)
    ├── db.py              # Connection handling, schema + sample data, `init-db` command
    ├── security.py        # Password hashing, rate limiting, login/admin decorators
    ├── validators.py      # Form validation
    ├── images.py          # Product image upload / download
    ├── routes/            # One blueprint per area of the site
    │   ├── main.py        # Home, search, product page
    │   ├── auth.py        # Register, login, logout
    │   ├── cart.py        # Cart and checkout
    │   ├── orders.py      # Order history
    │   └── admin.py       # Product and order management (/admin/...)
    ├── templates/
    └── static/
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
To (re)create tables and sample data without starting the server: `flask --app eshop init-db`.

Set the `SECRET_KEY` environment variable in production.

## Default admin account

- Email: admin@eshop.com
- Username: admin
- Password: admin123
