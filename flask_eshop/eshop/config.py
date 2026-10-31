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

    PRODUCTS_PER_PAGE = 12
