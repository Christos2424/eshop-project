import os
import secrets

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.exceptions import HTTPException

from . import db
from .config import Config

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

    from .routes import main, auth, cart, orders, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(cart.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(admin.bp)

    register_template_helpers(app)
    register_error_handlers(app)

    # Product images uploaded by admins
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Favicon route to prevent 404 errors
    @app.route('/favicon.ico')
    def favicon():
        try:
            return send_from_directory(os.path.join(app.static_folder, 'images'),
                                       'favicon.ico',
                                       mimetype='image/vnd.microsoft.icon')
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
    @app.context_processor
    def utility_processor():
        def get_image_url(image_url):
            if not image_url:
                return url_for('static', filename='images/placeholder.png')

            # If it starts with uploads/, it's a local file
            if image_url.startswith('uploads/'):
                return url_for('uploaded_file', filename=image_url.removeprefix('uploads/'))

            # Otherwise, it's an external URL
            return image_url

        # Get categories for header dropdown
        categories = []
        try:
            categories = db.get_categories()
        except Exception:
            pass

        return dict(get_image_url=get_image_url, global_categories=categories)


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def too_large(error):
        flash('File too large. Maximum size is 16MB.', 'danger')
        return redirect(request.referrer or url_for('main.home'))

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        message = 'Your session expired. Please try again.'
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': message, 'error': message}), 400
        flash(message, 'warning')
        return redirect(request.referrer or url_for('main.home'))

    @app.errorhandler(Exception)
    def handle_exception(error):
        # Let HTTP errors (405, 403, ...) keep their own status code
        if isinstance(error, HTTPException):
            return error
        flash('An unexpected error occurred. Please try again.', 'danger')
        return render_template('errors/500.html'), 500
