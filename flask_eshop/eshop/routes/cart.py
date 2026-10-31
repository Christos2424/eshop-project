from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify

from ..db import get_db, get_cursor
from ..security import login_required

bp = Blueprint('cart', __name__)


def is_ajax():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest'


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
        products = cur.fetchall()

    cart_items = []
    total = 0
    for product in products:
        qty = cart[str(product["product_id"])]
        item_total = product["price"] * qty
        cart_items.append({
            "product": product,
            "quantity": qty,
            "total": item_total
        })
        total += item_total

    found_ids = {str(product["product_id"]) for product in products}
    missing_ids = [pid for pid in product_ids if pid not in found_ids]
    return cart_items, total, missing_ids


@bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))

    def fail(message, flash_message=None, category='danger'):
        if is_ajax():
            return jsonify({'success': False, 'message': message})
        flash(flash_message or message, category)
        return redirect(request.referrer or url_for('main.home'))

    if not product_id:
        return fail('Invalid product')

    try:
        # Validate product exists
        with get_cursor() as cur:
            cur.execute("SELECT product_id, name, stock_quantity FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()

        if not product:
            return fail('Product not found')

        if product['stock_quantity'] == 0:
            return fail(f"{product['name']} is out of stock",
                        f"{product['name']} is currently out of stock", 'warning')

        # Check if requested quantity exceeds available stock
        if product['stock_quantity'] < quantity:
            return fail(f"Only {product['stock_quantity']} units available",
                        f"Only {product['stock_quantity']} units of {product['name']} available", 'warning')

        # Update cart
        cart = session.get('cart', {})
        new_quantity = cart.get(str(product_id), 0) + quantity

        # Final check to ensure we don't exceed stock
        if new_quantity > product['stock_quantity']:
            return fail(f"Cannot add more than {product['stock_quantity']} units",
                        f"Cannot add more than {product['stock_quantity']} units of {product['name']}", 'warning')

        cart[str(product_id)] = new_quantity
        session["cart"] = cart
        session.modified = True

        if is_ajax():
            return jsonify({
                'success': True,
                'message': f"{product['name']} added to cart!",
                'cart_count': sum(cart.values())
            })

        flash("Item added to cart!", "success")
        return redirect(request.referrer or url_for('main.home'))

    except Exception as e:
        return fail(f"Error: {str(e)}", f"Error adding to cart: {str(e)}")


@bp.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')

    if not product_id or not quantity:
        flash('Invalid request', 'danger')
        return redirect(url_for('cart.view_cart'))

    try:
        quantity = int(quantity)

        if 'cart' in session and str(product_id) in session['cart']:
            # Check if product is in stock before allowing quantity updates
            with get_cursor() as cur:
                cur.execute("SELECT stock_quantity FROM products WHERE product_id = ?", (product_id,))
                product = cur.fetchone()

            if product and product['stock_quantity'] == 0:
                flash('This product is out of stock and cannot be added to cart', 'warning')
                # Remove from cart if already there
                del session['cart'][str(product_id)]
                session.modified = True
                return redirect(url_for('cart.view_cart'))

            if product and quantity <= product['stock_quantity']:
                if quantity <= 0:
                    del session['cart'][str(product_id)]
                    flash('Item removed from cart', 'success')
                else:
                    session['cart'][str(product_id)] = quantity
                    flash('Cart updated successfully!', 'success')
            else:
                flash('Requested quantity not available', 'warning')

            session.modified = True
        else:
            flash('Item not found in cart', 'warning')

    except ValueError:
        flash('Invalid quantity', 'danger')
    except Exception as e:
        flash(f"Error updating cart: {str(e)}", 'danger')

    return redirect(url_for('cart.view_cart'))


@bp.route("/cart")
def view_cart():
    cart = session.get("cart")
    if not cart:
        return render_template("cart.html", cart_items=[], total=0)

    try:
        cart_items, total, missing_ids = load_cart_items(cart)

        # Remove any products from cart that weren't found in database
        if missing_ids:
            for pid in missing_ids:
                del cart[pid]
            session["cart"] = cart
            session.modified = True
            flash("Some items in your cart are no longer available and have been removed.", "warning")

        return render_template("cart.html", cart_items=cart_items, total=total)

    except Exception as e:
        flash(f"Error loading cart: {str(e)}", "danger")
        # If there's an error, clear the cart to prevent further issues
        session.pop('cart', None)
        return render_template("cart.html", cart_items=[], total=0)


@bp.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'cart' in session and 'product_id' in request.form:
        product_id = request.form['product_id']
        cart = session['cart']
        if str(product_id) in cart:
            del cart[str(product_id)]
            session['cart'] = cart
            session.modified = True
            flash('Item removed from cart', 'success')
    return redirect(url_for('cart.view_cart'))


@bp.route("/checkout", methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get("cart")
    if not cart:
        flash("Your cart is empty", 'warning')
        return redirect(url_for("cart.view_cart"))

    if request.method == 'GET':
        # Show checkout page with totals
        cart_items, total, _ = load_cart_items(cart)
        return render_template('checkout.html', cart_items=cart_items, total=total)

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
                f"SELECT product_id, price, stock_quantity, name FROM products WHERE product_id IN ({placeholders})",
                product_ids
            )
            products = {str(row['product_id']): dict(row) for row in cur.fetchall()}

            total = 0
            insufficient_stock = []

            # Check stock availability and calculate total
            for pid, qty in cart.items():
                if pid not in products:
                    db.rollback()
                    flash(f"Product ID {pid} no longer available", 'danger')
                    return redirect(url_for('cart.view_cart'))

                product = products[pid]
                if product['stock_quantity'] < qty:
                    insufficient_stock.append(f"{product['name']} (available: {product['stock_quantity']})")
                total += product['price'] * qty

            if insufficient_stock:
                db.rollback()
                flash(f"Insufficient stock for: {', '.join(insufficient_stock)}", 'danger')
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

            flash(f'Order #{order_id} placed successfully!', 'success')
            return redirect(url_for('orders.user_orders'))

        except Exception as e:
            db.rollback()
            raise e

    except Exception as e:
        flash(f"Checkout failed: {str(e)}", 'danger')
        return redirect(url_for('cart.view_cart'))
