import os

from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.exceptions import HTTPException

from . import db
from .config import Config


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if not app.config['DATABASE']:
        app.config['DATABASE'] = os.path.join(app.instance_path, 'eshop.db')
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')

    # Ensure instance and upload directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    from .routes import main, auth, cart, orders, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(cart.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(admin.bp)

    register_template_helpers(app)
    register_error_handlers(app)

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


def register_template_helpers(app):
    @app.context_processor
    def utility_processor():
        def get_image_url(image_url):
            if not image_url:
                return url_for('static', filename='images/placeholder.png')

            # If it starts with uploads/, it's a local file
            if image_url.startswith('uploads/'):
                return url_for('static', filename=image_url)

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
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500

    @app.errorhandler(413)
    def too_large(error):
        flash('File too large. Maximum size is 16MB.', 'danger')
        return redirect(request.referrer or url_for('main.home'))

    @app.errorhandler(Exception)
    def handle_exception(error):
        # Let HTTP errors (405, 403, ...) keep their own status code
        if isinstance(error, HTTPException):
            return error
        flash('An unexpected error occurred. Please try again.', 'danger')
        return render_template('500.html'), 500
