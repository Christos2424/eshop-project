from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from ..db import get_cursor
from ..security import hash_password, check_password, rate_limit, reset_rate_limit
from ..validators import validate_user_data

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Validate user data
        validation_errors = validate_user_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('register.html')

        try:
            with get_cursor() as cur:
                # Check if user exists
                cur.execute('SELECT * FROM users WHERE email = ?', (email,))
                if cur.fetchone():
                    flash('Email already registered!', 'danger')
                    return render_template('register.html')

                cur.execute('SELECT * FROM users WHERE username = ?', (username,))
                if cur.fetchone():
                    flash('Username already taken!', 'danger')
                    return render_template('register.html')

                hashed_pw = hash_password(password)
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, hashed_pw)
                )

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            flash(f"Registration error: {str(e)}", 'danger')
            return render_template('register.html')

    return render_template('register.html')


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        next_page = request.form.get('next') or request.args.get('next')

        # Rate limiting
        if not rate_limit(email):
            flash('Too many login attempts. Please try again in 15 minutes.', 'danger')
            return render_template('login.html')

        try:
            with get_cursor() as cur:
                cur.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = cur.fetchone()

            if user and check_password(user['password_hash'], password):
                session["user_id"] = user['user_id']
                session["username"] = user['username']
                session["role"] = user['role']
                flash('Login successful!', 'success')

                # Clear rate limiting for successful login
                reset_rate_limit(email)

                # Redirect to the requested page or home
                return redirect(next_page or url_for('main.home'))
            else:
                flash('Invalid email or password', 'danger')
                return render_template('login.html')

        except Exception as e:
            flash(f"Login error: {str(e)}", 'danger')
            return render_template("login.html")

    # GET request - show login form
    next_page = request.args.get('next', '')
    return render_template('login.html', next=next_page)


@bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))
