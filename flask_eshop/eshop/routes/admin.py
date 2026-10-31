from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from ..db import get_cursor
from ..i18n import gettext as _
from ..images import save_uploaded_file, download_image_from_url
from ..security import admin_required
from ..validators import validate_product_data

bp = Blueprint('admin', __name__, url_prefix='/admin')

ORDER_STATUSES = ['pending', 'paid', 'shipped', 'cancelled']


@bp.before_request
@admin_required
def require_admin():
    """Every route in this blueprint is admin-only"""


def greek_fields(form):
    """Optional Greek name and description from the product form (None when left empty)"""
    return form.get('name_el', '').strip() or None, form.get('description_el', '').strip() or None


def next_product_id():
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(product_id), 0) + 1 as next_id FROM products")
        return cur.fetchone()['next_id']


@bp.route('/products')
def products():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products ORDER BY created_at DESC")
            products = cur.fetchall()

            # Fetch orders with user information
            cur.execute("""
                SELECT o.order_id, o.total, o.status, o.created_at,
                       u.username, u.email
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                ORDER BY o.created_at DESC
            """)
            orders = cur.fetchall()

        return render_template('admin/products.html', products=products, orders=orders)
    except Exception as e:
        flash(_('Error: {error}', error=str(e)), 'danger')
        return redirect(url_for('main.home'))


@bp.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        validation_errors = validate_product_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(_(error), 'danger')
            return render_template('admin/add_product.html')

        name = request.form['name']
        description = request.form['description']
        name_el, description_el = greek_fields(request.form)
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        image_url = request.form.get('image_url', '').strip()

        image_path = None

        try:
            # Handle image upload or URL
            file = request.files.get('image_file')
            if file and file.filename != '':
                image_path = save_uploaded_file(file, next_product_id())
                if image_path:
                    flash(_('Image uploaded successfully!'), 'success')

            # If no file uploaded but URL provided
            if not image_path and image_url:
                image_path = download_image_from_url(image_url, next_product_id())
                if image_path:
                    flash(_('Image downloaded from URL successfully!'), 'success')
                else:
                    flash(_('Failed to download image from URL'), 'warning')

            with get_cursor() as cur:
                cur.execute(
                    """INSERT INTO products
                    (name, name_el, description, description_el, price, stock_quantity, category, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, name_el, description, description_el, price, stock, category, image_path)
                )

            flash(_('Product added successfully!'), 'success')
            return redirect(url_for('admin.products'))
        except Exception as e:
            flash(_('Error adding product: {error}', error=str(e)), 'danger')
            return render_template('admin/add_product.html')

    return render_template('admin/add_product.html')


@bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    try:
        with get_cursor() as cur:
            if request.method == 'POST':
                validation_errors = validate_product_data(request.form)
                if validation_errors:
                    for error in validation_errors:
                        flash(_(error), 'danger')
                    return redirect(url_for('admin.edit_product', product_id=product_id))

                name = request.form['name']
                description = request.form['description']
                name_el, description_el = greek_fields(request.form)
                price = float(request.form['price'])
                stock = int(request.form['stock'])
                category = request.form['category']
                image_url = request.form.get('image_url', '').strip()

                # Get current product data
                cur.execute("SELECT image_url FROM products WHERE product_id = ?", (product_id,))
                current_product = cur.fetchone()
                image_path = current_product['image_url'] if current_product else None  # Keep current image by default

                # Handle image upload
                file = request.files.get('image_file')
                if file and file.filename != '':
                    new_image_path = save_uploaded_file(file, product_id)
                    if new_image_path:
                        image_path = new_image_path
                        flash(_('New image uploaded successfully!'), 'success')

                # Handle image URL
                if not image_path and image_url:
                    new_image_path = download_image_from_url(image_url, product_id)
                    if new_image_path:
                        image_path = new_image_path
                        flash(_('New image downloaded from URL successfully!'), 'success')
                    else:
                        flash(_('Failed to download image from URL'), 'warning')

                # If "remove image" is checked, set image_path to None
                if request.form.get('remove_image'):
                    image_path = None
                    flash(_('Image removed successfully!'), 'success')

                cur.execute(
                    """UPDATE products
                    SET name=?, name_el=?, description=?, description_el=?, price=?, stock_quantity=?,
                        category=?, image_url=?
                    WHERE product_id=?""",
                    (name, name_el, description, description_el, price, stock, category, image_path, product_id)
                )
                flash(_('Product updated successfully!'), 'success')
                return redirect(url_for('admin.products'))
            else:
                cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
                product = cur.fetchone()
                if not product:
                    flash(_('Product not found'), 'danger')
                    return redirect(url_for('admin.products'))
                return render_template('admin/edit_product.html', product=product)
    except Exception as e:
        flash(_('Error: {error}', error=str(e)), 'danger')
        return redirect(url_for('admin.products'))


@bp.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        with get_cursor() as cur:
            # Check if product exists in any orders
            cur.execute("SELECT COUNT(*) FROM order_items WHERE product_id = ?", (product_id,))
            order_count = cur.fetchone()[0]

            if order_count > 0:
                flash(_('Cannot delete product that has been ordered. Consider archiving instead.'), 'danger')
            else:
                cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
                flash(_('Product deleted successfully!'), 'success')
    except Exception as e:
        flash(_('Error deleting product: {error}', error=str(e)), 'danger')

    return redirect(url_for('admin.products'))


@bp.route('/update_order/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')

        if new_status not in ORDER_STATUSES:
            return jsonify({'success': False, 'error': _('Invalid status')})

        with get_cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = ? WHERE order_id = ?",
                (new_status, order_id)
            )

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
