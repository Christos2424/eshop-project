"""WSGI file for PythonAnywhere. On the Web tab, open the WSGI configuration file,
replace its contents with this file and change PROJECT to your project folder."""
import os
import sys

from dotenv import load_dotenv

PROJECT = '/home/YOUR_USERNAME/eshop-project/flask_eshop'

sys.path.insert(0, PROJECT)
# .env holds SECRET_KEY, ADMIN_PASSWORD and SESSION_COOKIE_SECURE (the flask command loads it, WSGI doesn't)
load_dotenv(os.path.join(PROJECT, '.env'))

from eshop import create_app  # noqa: E402

application = create_app()
