from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app

from ..db import get_cursor
from ..i18n import gettext as _
from ..images import save_uploaded_file, download_image_from_url
from ..security import admin_required
from ..validators import validate_product_data

bp = Blueprint('admin', __name__, url_prefix='/admin')

ORDER_STATUSES = ['pending', 'paid', 'shipped', 'cancelled']


class NotEnoughStock(Exception):
    """Raised inside a transaction to roll it back when an order can't be reopened"""


@bp.before_request
@admin_required
def require_admin():
    """Every route in this blueprint is admin-only"""


def greek_fields(form):
    """Optional Greek name and description from the product form (None when left empty)"""
    return form.get('name_el', '').strip() or None, form.get('description_el', '').strip() or None


def product_fields(form):
    """The product form's values, cleaned up and converted (call after validate_product_data)"""
    name_el, description_el = greek_fields(form)
    return {
        'name': form['name'].strip(),
        'description': form['description'].strip(),
        'name_el': name_el,
        'description_el': description_el,
        'price': round(float(form['price']), 2),
        'stock_quantity': int(form['stock']),
        'category': form.get('category', '').strip(),
    }


def form_values(product, form):
    """The product with what the admin typed on top, to refill the form after an error"""
    values = dict(product)
    for field in ('name', 'description', 'name_el', 'description_el', 'category'):
        values[field] = form.get(field, values.get(field) or '')
    # Price is shown with "%.2f", so only take it when it's a number
    try:
        values['price'] = float(form.get('price', ''))
    except ValueError:
        pass
    values['stock_quantity'] = form.get('stock', values['stock_quantity'])
    return values


def next_product_id():
    with get_cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(product_id), 0) + 1 as next_id FROM products")
        return cur.fetchone()['next_id']


def new_image(form, files, product_id, current_image=None):
    """Path of a newly uploaded or downloaded image, or None when none was given or it failed.

    The edit form shows an external image's URL; leaving it unchanged doesn't download it again.
    """
    file = files.get('image_file')
    if file and file.filename != '':
        image_path = save_uploaded_file(file, product_id)
        if image_path:
            flash(_('Image uploaded successfully!'), 'success')
            return image_path

    image_url = form.get('image_url', '').strip()
    if image_url and image_url != current_image:
        image_path = download_image_from_url(image_url, product_id)
        if image_path:
            flash(_('Image downloaded from URL successfully!'), 'success')
            return image_path
        flash(_('Failed to download image from URL'), 'warning')
    return None


@bp.route('/products')
def products():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products ORDER BY created_at DESC")
            products = cur.fetchall()
        return render_template('admin/products.html', products=products)
    except Exception:
        current_app.logger.exception('Loading admin products failed')
        flash(_('An unexpected error occurred. Please try again.'), 'danger')
        return redirect(url_for('main.home'))


@bp.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        validation_errors = validate_product_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(_(error), 'danger')
            return render_template('admin/add_product.html')

        fields = product_fields(request.form)
        try:
            image_path = new_image(request.form, request.files, next_product_id())

            with get_cursor() as cur:
                cur.execute(
                    """INSERT INTO products
                    (name, name_el, description, description_el, price, stock_quantity, category, image_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (fields['name'], fields['name_el'], fields['description'], fields['description_el'],
                     fields['price'], fields['stock_quantity'], fields['category'], image_path)
                )

            flash(_('Product added successfully!'), 'success')
            return redirect(url_for('admin.products'))
        except Exception:
            current_app.logger.exception('Adding a product failed')
            flash(_('An unexpected error occurred. Please try again.'), 'danger')
            return render_template('admin/add_product.html')

    return render_template('admin/add_product.html')


@bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()
        if not product:
            flash(_('Product not found'), 'danger')
            return redirect(url_for('admin.products'))

        if request.method == 'GET':
            return render_template('admin/edit_product.html', product=product)

        validation_errors = validate_product_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(_(error), 'danger')
            return render_template('admin/edit_product.html', product=form_values(product, request.form))

        fields = product_fields(request.form)

        # Keep the current image unless it's removed or replaced
        image_path = product['image_url']
        if request.form.get('remove_image'):
            image_path = None
            flash(_('Image removed successfully!'), 'success')
        image_path = new_image(request.form, request.files, product_id, product['image_url']) or image_path

        with get_cursor() as cur:
            cur.execute(
                """UPDATE products
                SET name=?, name_el=?, description=?, description_el=?, price=?, stock_quantity=?,
                    category=?, image_url=?
                WHERE product_id=?""",
                (fields['name'], fields['name_el'], fields['description'], fields['description_el'],
                 fields['price'], fields['stock_quantity'], fields['category'], image_path, product_id)
            )
        flash(_('Product updated successfully!'), 'success')
        return redirect(url_for('admin.products'))
    except Exception:
        current_app.logger.exception('Editing product %s failed', product_id)
        flash(_('An unexpected error occurred. Please try again.'), 'danger')
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
                cur.execute("DELETE FROM reviews WHERE product_id = ?", (product_id,))
                cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
                if cur.rowcount:
                    flash(_('Product deleted successfully!'), 'success')
                else:
                    flash(_('Product not found'), 'danger')
    except Exception:
        current_app.logger.exception('Deleting product %s failed', product_id)
        flash(_('An unexpected error occurred. Please try again.'), 'danger')

    return redirect(url_for('admin.products'))


@bp.route('/update_order/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    if new_status not in ORDER_STATUSES:
        return jsonify({'success': False, 'error': _('Invalid status')}), 400

    try:
        with get_cursor() as cur:
            cur.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
            order = cur.fetchone()
            if not order:
                return jsonify({'success': False, 'error': _('Order not found')}), 404

            old_status = order['status']
            cur.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
            items = cur.fetchall()

            # Cancelling puts the items back in stock; reopening a cancelled order takes them out again
            if new_status == 'cancelled' and old_status != 'cancelled':
                for item in items:
                    cur.execute("UPDATE products SET stock_quantity = stock_quantity + ? WHERE product_id = ?",
                                (item['quantity'], item['product_id']))
            elif old_status == 'cancelled' and new_status != 'cancelled':
                for item in items:
                    cur.execute("""UPDATE products SET stock_quantity = stock_quantity - ?
                                   WHERE product_id = ? AND stock_quantity >= ?""",
                                (item['quantity'], item['product_id'], item['quantity']))
                    if cur.rowcount != 1:
                        raise NotEnoughStock()

            cur.execute("UPDATE orders SET status = ? WHERE order_id = ?", (new_status, order_id))

        return jsonify({'success': True})
    except NotEnoughStock:
        return jsonify({'success': False, 'error': _('Not enough stock to reopen this order')}), 409
    except Exception:
        current_app.logger.exception('Updating order %s failed', order_id)
        return jsonify({'success': False, 'error': _('Error updating order status')}), 500
