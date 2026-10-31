from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app

from ..db import get_db, get_cursor
from ..i18n import gettext as _, localized
from ..security import login_required
from ..utils import is_ajax, product_to_dict

bp = Blueprint('cart', __name__)


def load_cart_items(cart):
    """Return (cart_items, total, missing_ids) for the products in the session cart"""
    product_ids = list(cart.keys())
    if not product_ids:
        return [], 0, []

    placeholders = ','.join(['?'] * len(product_ids))
    with get_cursor() as cur:
        cur.execute(
            f"SELECT * FROM products WHERE product_id IN ({placeholders})",
            product_ids
        )
        products = {str(product["product_id"]): product for product in cur.fetchall()}

    # Stable order by product id (the session doesn't keep the order items were added in)
    cart_items = []
    total = 0
    for pid in sorted(product_ids, key=int):
        if pid not in products:
            continue
        product = products[pid]
        qty = cart[pid]
        item_total = product["price"] * qty
        cart_items.append({
            "product": product,
            "quantity": qty,
            "total": item_total
        })
        total += item_total

    missing_ids = [pid for pid in product_ids if pid not in products]
    return cart_items, total, missing_ids


def get_cart_items():
    """Load the session cart, dropping products that no longer exist.

    Returns (cart_items, subtotal, removed) where removed is True if anything was dropped.
    """
    cart = session.get('cart', {})
    cart_items, subtotal, missing_ids = load_cart_items(cart)

    if missing_ids:
        for pid in missing_ids:
            del cart[pid]
        session["cart"] = cart
        session.modified = True

    return cart_items, subtotal, bool(missing_ids)


def cart_totals(subtotal):
    """Shipping, tax and grand total for a cart subtotal"""
    config = current_app.config
    threshold = config['FREE_SHIPPING_THRESHOLD']
    shipping = 0 if subtotal == 0 or subtotal >= threshold else config['SHIPPING_FEE']
    tax = round(subtotal * config['TAX_RATE'], 2)
    return {
        'subtotal': round(subtotal, 2),
        'shipping': shipping,
        'tax': tax,
        'total': round(subtotal + shipping + tax, 2),
        'free_shipping_threshold': threshold,
        'free_shipping_remaining': round(max(threshold - subtotal, 0), 2),
    }


def cart_payload():
    """The whole cart as JSON for the cart drawer and the cart page's JavaScript"""
    cart_items, subtotal, _removed = get_cart_items()
    items = [
        {**product_to_dict(item['product']), 'quantity': item['quantity'], 'line_total': round(item['total'], 2)}
        for item in cart_items
    ]
    return {'count': sum(item['quantity'] for item in items), 'items': items, **cart_totals(subtotal)}


def cart_response(success, message, category=None, redirect_to=None):
    """JSON with the updated cart for AJAX requests, otherwise flash and redirect"""
    if is_ajax():
        return jsonify({'success': success, 'message': message, 'cart': cart_payload()})
    flash(message, category or ('success' if success else 'danger'))
    return redirect(redirect_to or url_for('cart.view_cart'))


def save_cart(cart):
    session['cart'] = cart
    session.modified = True


@bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    try:
        quantity = int(request.form.get('quantity', 1))
    except ValueError:
        quantity = 0

    def fail(message, flash_message=None, category='danger'):
        if is_ajax():
            return jsonify({'success': False, 'message': message})
        flash(flash_message or message, category)
        return redirect(request.referrer or url_for('main.home'))

    if not product_id:
        return fail(_('Invalid product'))

    if quantity < 1:
        return fail(_('Invalid quantity'))

    try:
        # Validate product exists
        with get_cursor() as cur:
            cur.execute("SELECT product_id, name, name_el, stock_quantity FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()

        if not product:
            return fail(_('Product not found'))

        name = localized(product, 'name')
        stock = product['stock_quantity']
        if stock == 0:
            return fail(_('{name} is out of stock', name=name),
                        _('{name} is currently out of stock', name=name), 'warning')

        # Check if requested quantity exceeds available stock
        if stock < quantity:
            return fail(_('Only {n} units available', n=stock),
                        _('Only {n} units of {name} available', n=stock, name=name), 'warning')

        # Update cart
        cart = session.get('cart', {})
        new_quantity = cart.get(str(product_id), 0) + quantity

        # Final check to ensure we don't exceed stock
        if new_quantity > stock:
            return fail(_('Cannot add more than {n} units', n=stock),
                        _('Cannot add more than {n} units of {name}', n=stock, name=name), 'warning')

        cart[str(product_id)] = new_quantity
        save_cart(cart)

        if is_ajax():
            payload = cart_payload()
            return jsonify({
                'success': True,
                'message': _('{name} added to cart!', name=name),
                'cart_count': payload['count'],
                'cart': payload
            })

        flash(_('Item added to cart!'), 'success')
        return redirect(request.referrer or url_for('main.home'))

    except Exception as e:
        return fail(_('Error: {error}', error=str(e)), _('Error adding to cart: {error}', error=str(e)))


@bp.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id', '')
    cart = session.get('cart', {})

    try:
        quantity = int(request.form.get('quantity', ''))
    except ValueError:
        return cart_response(False, _('Invalid quantity'))

    if product_id not in cart:
        return cart_response(False, _('Item not found in cart'), 'warning')

    try:
        with get_cursor() as cur:
            cur.execute("SELECT stock_quantity FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()

        # Products that were deleted or sold out can't stay in the cart
        if not product or product['stock_quantity'] == 0:
            del cart[product_id]
            save_cart(cart)
            return cart_response(False, _('This product is out of stock and was removed from your cart'), 'warning')

        if quantity > product['stock_quantity']:
            return cart_response(False, _('Only {n} units available', n=product['stock_quantity']), 'warning')

        if quantity <= 0:
            del cart[product_id]
            message = _('Item removed from cart')
        else:
            cart[product_id] = quantity
            message = _('Cart updated successfully!')
        save_cart(cart)
        return cart_response(True, message)

    except Exception as e:
        return cart_response(False, _('Error updating cart: {error}', error=str(e)))


@bp.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    product_id = request.form.get('product_id', '')
    cart = session.get('cart', {})

    if product_id not in cart:
        return cart_response(False, _('Item not found in cart'), 'warning')

    del cart[product_id]
    save_cart(cart)
    return cart_response(True, _('Item removed from cart'))


@bp.route('/cart/data')
def cart_data():
    """Current cart as JSON, loaded when the cart drawer opens"""
    return jsonify(cart_payload())


@bp.route("/cart")
def view_cart():
    try:
        cart_items, subtotal, removed = get_cart_items()
        if removed:
            flash(_('Some items in your cart are no longer available and have been removed.'), 'warning')

        return render_template("cart/cart.html", cart_items=cart_items, totals=cart_totals(subtotal))

    except Exception as e:
        flash(_('Error loading cart: {error}', error=str(e)), 'danger')
        # If there's an error, clear the cart to prevent further issues
        session.pop('cart', None)
        return render_template("cart/cart.html", cart_items=[], totals=cart_totals(0))


@bp.route("/checkout", methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get("cart")
    if not cart:
        flash(_('Your cart is empty'), 'warning')
        return redirect(url_for("cart.view_cart"))

    if request.method == 'GET':
        # Show checkout page with totals
        cart_items, subtotal, _removed = get_cart_items()
        return render_template('cart/checkout.html', cart_items=cart_items, totals=cart_totals(subtotal))

    # POST request - process the actual checkout
    try:
        user_id = session["user_id"]
        product_ids = [int(pid) for pid in cart.keys()]

        db = get_db()
        db.execute("BEGIN TRANSACTION")

        try:
            cur = db.cursor()
            placeholders = ','.join(['?'] * len(product_ids))

            cur.execute(
                f"SELECT product_id, price, stock_quantity, name, name_el FROM products WHERE product_id IN ({placeholders})",
                product_ids
            )
            products = {str(row['product_id']): dict(row) for row in cur.fetchall()}

            total = 0
            insufficient_stock = []

            # Check stock availability and calculate total
            for pid, qty in cart.items():
                if pid not in products:
                    db.rollback()
                    flash(_('Product ID {id} no longer available', id=pid), 'danger')
                    return redirect(url_for('cart.view_cart'))

                product = products[pid]
                if product['stock_quantity'] < qty:
                    insufficient_stock.append(_('{name} (available: {n})', name=localized(product, 'name'), n=product['stock_quantity']))
                total += product['price'] * qty

            if insufficient_stock:
                db.rollback()
                flash(_('Insufficient stock for: {items}', items=', '.join(insufficient_stock)), 'danger')
                return redirect(url_for('cart.view_cart'))

            # Create order
            cur.execute(
                "INSERT INTO orders (user_id, total) VALUES (?, ?)",
                (user_id, total)
            )
            order_id = cur.lastrowid

            # Add order items and update stock
            for pid, qty in cart.items():
                product = products[pid]
                cur.execute(
                    """INSERT INTO order_items
                    (order_id, product_id, quantity, price_at_purchase)
                    VALUES (?, ?, ?, ?)""",
                    (order_id, int(pid), qty, product['price'])
                )
                cur.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - ? WHERE product_id = ?",
                    (qty, int(pid))
                )

            db.commit()

            # Clear cart
            session.pop('cart', None)
            session.modified = True

            flash(_('Order #{id} placed successfully!', id=order_id), 'success')
            return redirect(url_for('orders.user_orders'))

        except Exception as e:
            db.rollback()
            raise e

    except Exception as e:
        flash(_('Checkout failed: {error}', error=str(e)), 'danger')
        return redirect(url_for('cart.view_cart'))
