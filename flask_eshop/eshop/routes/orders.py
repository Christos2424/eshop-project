from flask import Blueprint, render_template, session, flash, jsonify, url_for

from ..db import get_cursor
from ..i18n import gettext as _, localized, name_sql
from ..images import image_src, placeholder_art
from ..security import login_required

bp = Blueprint('orders', __name__)


@bp.route('/orders')
@login_required
def user_orders():
    is_admin = session.get('role') == 'admin'
    template = 'admin/orders.html' if is_admin else 'orders/user_orders.html'

    # Product names in the current language
    product_name = name_sql('p.')

    try:
        with get_cursor() as cur:
            if is_admin:
                # Admin sees all orders with customer info
                cur.execute(f"""
                    SELECT o.*,
                           u.username,
                           u.email,
                           GROUP_CONCAT({product_name} || ' (x' || oi.quantity || ')') as product_names
                    FROM orders o
                    JOIN users u ON o.user_id = u.user_id
                    JOIN order_items oi ON o.order_id = oi.order_id
                    JOIN products p ON oi.product_id = p.product_id
                    GROUP BY o.order_id
                    ORDER BY o.created_at DESC
                """)
            else:
                # Regular users only see their own orders
                cur.execute(f"""
                    SELECT o.*,
                           GROUP_CONCAT({product_name} || ' (x' || oi.quantity || ')') as product_names
                    FROM orders o
                    JOIN order_items oi ON o.order_id = oi.order_id
                    JOIN products p ON oi.product_id = p.product_id
                    WHERE o.user_id = ?
                    GROUP BY o.order_id
                    ORDER BY o.created_at DESC
                """, (session['user_id'],))
            orders = cur.fetchall()
        return render_template(template, orders=orders)
    except Exception as e:
        flash(_('Error loading orders: {error}', error=str(e)), 'danger')
        return render_template(template, orders=[])


@bp.route('/orders/<int:order_id>/items')
@login_required
def order_items(order_id):
    """Line items of one order as JSON, for the order details modal"""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order = cur.fetchone()

        # Customers can only see their own orders; admins can see all
        if not order or (session.get('role') != 'admin' and order['user_id'] != session['user_id']):
            return jsonify({'success': False, 'error': _('Order not found')}), 404

        cur.execute("""
            SELECT oi.quantity, oi.price_at_purchase, p.product_id, p.name, p.name_el, p.category, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = ?
        """, (order_id,))
        items = cur.fetchall()

    return jsonify({
        'success': True,
        'order': {
            'id': order['order_id'],
            'status': order['status'],
            'created_at': order['created_at'],
            'total': order['total'],
        },
        'items': [{
            'name': localized(item, 'name'),
            'quantity': item['quantity'],
            'price': item['price_at_purchase'],
            'line_total': round(item['price_at_purchase'] * item['quantity'], 2),
            'image': image_src(item['image_url']),
            'art': placeholder_art(item['category']),
            'url': url_for('main.product_detail', product_id=item['product_id']),
        } for item in items],
    })
