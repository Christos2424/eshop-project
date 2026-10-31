import re


def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    return len(password) >= 6


def validate_product_data(data):
    errors = []

    if len(data.get('name', '').strip()) < 2:
        errors.append("Product name must be at least 2 characters")

    try:
        price = float(data.get('price', 0))
        if price < 0:  # Allow free products
            errors.append("Price cannot be negative")
    except (ValueError, TypeError):
        errors.append("Price must be a valid number")

    try:
        stock = int(data.get('stock', 0))
        if stock < 0:  # Allow 0 stock
            errors.append("Stock cannot be negative")
    except (ValueError, TypeError):
        errors.append("Stock must be a valid integer")

    if len(data.get('description', '').strip()) < 10:
        errors.append("Description must be at least 10 characters")

    return errors


def validate_user_data(data):
    errors = []

    username = data.get('username', '').strip()
    if len(username) < 3:
        errors.append("Username must be at least 3 characters")
    if not username.isalnum():
        errors.append("Username can only contain letters and numbers")

    email = data.get('email', '').strip()
    if not validate_email(email):
        errors.append("Invalid email address")

    password = data.get('password', '')
    if not validate_password(password):
        errors.append("Password must be at least 6 characters")

    if password != data.get('confirm_password', ''):
        errors.append("Passwords do not match")

    return errors
