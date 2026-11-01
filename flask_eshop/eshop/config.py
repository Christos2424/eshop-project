import os


class Config:
    # If unset, a random key is generated and stored in instance/secret_key
    SECRET_KEY = os.environ.get('SECRET_KEY')

    # Database path; defaults to instance/eshop.db (set in create_app)
    DATABASE = os.environ.get('DATABASE')

    # Image upload configuration; uploads are stored in instance/uploads
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    IMAGE_DOWNLOAD_TIMEOUT = 10  # seconds

    # CSRF tokens stay valid for the whole session
    WTF_CSRF_TIME_LIMIT = None

    # Don't send the session cookie with requests started by other sites
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Set SESSION_COOKIE_SECURE=1 once the site is served over HTTPS, so the cookie is never sent over HTTP
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE') == '1'

    PRODUCTS_PER_PAGE = 12
    SEARCH_SUGGESTIONS = 6

    # Cart pricing, shown in the cart and at checkout
    FREE_SHIPPING_THRESHOLD = 50
    SHIPPING_FEE = 9.99
    TAX_RATE = 0.08
