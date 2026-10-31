import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database path; defaults to instance/eshop.db (set in create_app)
    DATABASE = os.environ.get('DATABASE')

    # Image upload configuration
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    PRODUCTS_PER_PAGE = 12
