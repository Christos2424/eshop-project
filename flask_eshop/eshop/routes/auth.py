from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app

from ..db import get_cursor
from ..i18n import gettext as _
from ..security import hash_password, check_password, rate_limit, reset_rate_limit
from ..utils import is_safe_redirect
from ..validators import validate_user_data

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        # Emails are stored lowercase so Foo@x.com and foo@x.com are the same account
        email = request.form['email'].strip().lower()
        password = request.form['password']

        # Validate user data
        validation_errors = validate_user_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(_(error), 'danger')
            return render_template('auth/register.html')

        try:
            with get_cursor() as cur:
                # Check if user exists
                cur.execute('SELECT 1 FROM users WHERE lower(email) = ?', (email,))
                if cur.fetchone():
                    flash(_('Email already registered!'), 'danger')
                    return render_template('auth/register.html')

                cur.execute('SELECT 1 FROM users WHERE username = ? COLLATE NOCASE', (username,))
                if cur.fetchone():
                    flash(_('Username already taken!'), 'danger')
                    return render_template('auth/register.html')

                hashed_pw = hash_password(password)
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, hashed_pw)
                )

            flash(_('Registration successful! Please log in.'), 'success')
            return redirect(url_for('auth.login'))

        except Exception:
            current_app.logger.exception('Registration failed')
            flash(_('An unexpected error occurred. Please try again.'), 'danger')
            return render_template('auth/register.html')

    return render_template('auth/register.html')


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        next_page = request.form.get('next') or request.args.get('next')

        # Rate limiting
        if not rate_limit(email):
            flash(_('Too many login attempts. Please try again in 15 minutes.'), 'danger')
            return render_template('auth/login.html')

        try:
            with get_cursor() as cur:
                cur.execute('SELECT * FROM users WHERE lower(email) = ?', (email,))
                user = cur.fetchone()

            if user and check_password(user['password_hash'], password):
                # Start a fresh session, keeping only the cart and the chosen language
                kept = {key: session[key] for key in ('cart', 'lang') if key in session}
                session.clear()
                session.update(kept)
                session["user_id"] = user['user_id']
                session["username"] = user['username']
                session["role"] = user['role']
                flash(_('Login successful!'), 'success')

                # Clear rate limiting for successful login
                reset_rate_limit(email)

                # Redirect to the requested page (only on this site) or home
                if not is_safe_redirect(next_page):
                    next_page = url_for('main.home')
                return redirect(next_page)
            else:
                flash(_('Invalid email or password'), 'danger')
                return render_template('auth/login.html')

        except Exception:
            current_app.logger.exception('Login failed')
            flash(_('An unexpected error occurred. Please try again.'), 'danger')
            return render_template("auth/login.html")

    # GET request - show login form
    next_page = request.args.get('next', '')
    return render_template('auth/login.html', next=next_page)


# POST only, so another site can't log people out with a link or an <img>
@bp.route('/logout', methods=['POST'])
def logout():
    # Keep the chosen language after logging out
    lang = session.get('lang')
    session.clear()
    if lang:
        session['lang'] = lang
    flash(_('You have been logged out'), 'info')
    return redirect(url_for('main.home'))
