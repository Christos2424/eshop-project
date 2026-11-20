import time
from functools import wraps

import bcrypt
from flask import session, flash, redirect, url_for, request

from .i18n import gettext as _

# Rate limiting storage
login_attempts = {}


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def check_password(hashed_password, user_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)


# Decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash(_('Admin access required'), 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash(_('Please log in to access this page'), 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def rate_limit(key, max_attempts=5, window=900):  # 15 minutes
    """Simple rate limiting"""
    current_time = time.time()
    if key not in login_attempts:
        login_attempts[key] = []

    # Remove old attempts
    login_attempts[key] = [attempt_time for attempt_time in login_attempts[key]
                           if current_time - attempt_time < window]

    if len(login_attempts[key]) >= max_attempts:
        return False

    login_attempts[key].append(current_time)
    return True


def reset_rate_limit(key):
    login_attempts.pop(key, None)
