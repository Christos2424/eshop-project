import os
import secrets

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.exceptions import HTTPException

from . import db, i18n
from .config import Config
from .i18n import gettext as _
from .images import image_src, placeholder_art

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Ensure instance directory exists
    os.makedirs(app.instance_path, exist_ok=True)

    if not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = load_or_create_secret_key(app.instance_path)
    if not app.config['DATABASE']:
        app.config['DATABASE'] = os.path.join(app.instance_path, 'eshop.db')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    csrf.init_app(app)
    db.init_app(app)
    i18n.load_catalogs(app)

    from .routes import main, auth, cart, orders, admin, api, reviews
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(cart.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(reviews.bp)

    register_template_helpers(app)
    register_error_handlers(app)

    @app.after_request
    def security_headers(response):
        # Stop browsers guessing file types (an upload named .png can't run as HTML)
        # and other sites from framing the shop
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        return response

    # Product images uploaded by admins
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Favicon route to prevent 404 errors
    @app.route('/favicon.ico')
    def favicon():
        try:
            return send_from_directory(os.path.join(app.static_folder, 'images'),
                                       'favicon.svg',
                                       mimetype='image/svg+xml')
        except Exception:
            # If favicon doesn't exist, return empty response
            return '', 204

    return app


def load_or_create_secret_key(instance_path):
    """Read the secret key from instance/secret_key, generating it on first run"""
    path = os.path.join(instance_path, 'secret_key')
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(path, 'w') as f:
        f.write(key)
    return key


def register_template_helpers(app):
    @app.template_filter('currency')
    def currency(value):
        return f"{value or 0:,.2f} €"

    # Translations: {{ _('Text') }}, {{ ngettext('{n} item', '{n} items', n) }}, {{ product|localized('name') }}
    app.jinja_env.globals.update(
        _=i18n.template_gettext,
        ngettext=i18n.template_ngettext,
        category_label=i18n.category_label,
        placeholder_art=placeholder_art,
        LANGUAGES=i18n.LANGUAGES,
    )
    app.jinja_env.filters['localized'] = i18n.localized
    translations_version = i18n.catalog_version(app)

    @app.context_processor
    def language_processor():
        return dict(current_language=i18n.get_locale(), translations_version=translations_version)

    @app.context_processor
    def utility_processor():
        def get_image_url(image_url):
            return image_src(image_url) or url_for('static', filename='images/placeholder.svg')

        # Get categories (with product counts) for the header sidebar and filter chips
        categories = []
        try:
            categories = db.get_category_counts()
        except Exception:
            pass

        cart_count = sum(session.get('cart', {}).values())

        return dict(get_image_url=get_image_url, image_src=image_src,
                    global_categories=categories, cart_count=cart_count)


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    def wants_json():
        return request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    @app.errorhandler(413)
    def too_large(error):
        message = _('File too large. Maximum size is 16MB.')
        if wants_json():
            return jsonify({'success': False, 'message': message, 'error': message}), 413
        flash(message, 'danger')
        return redirect(request.referrer or url_for('main.home'))

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = _('Your session expired. Please try again.')
        if wants_json():
            return jsonify({'success': False, 'message': message, 'error': message}), 400
        flash(message, 'warning')
        return redirect(request.referrer or url_for('main.home'))

    @app.errorhandler(Exception)
    def handle_exception(error):
        # Let HTTP errors (405, 403, ...) keep their own status code
        if isinstance(error, HTTPException):
            return error
        app.logger.exception('Unhandled error on %s %s', request.method, request.path)
        message = _('An unexpected error occurred. Please try again.')
        if wants_json():
            return jsonify({'success': False, 'message': message, 'error': message}), 500
        return render_template('errors/500.html'), 500
