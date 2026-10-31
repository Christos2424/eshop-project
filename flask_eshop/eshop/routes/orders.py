from flask import Blueprint, render_template, session, flash

from ..db import get_cursor
from ..security import login_required

bp = Blueprint('orders', __name__)


@bp.route('/orders')
@login_required
def user_orders():
    is_admin = session.get('role') == 'admin'
    template = 'admin/orders.html' if is_admin else 'orders/user_orders.html'

    try:
        with get_cursor() as cur:
            if is_admin:
                # Admin sees all orders with customer info
                cur.execute("""
                    SELECT o.*,
                           u.username,
                           u.email,
                           GROUP_CONCAT(p.name || ' (x' || oi.quantity || ')') as product_names
                    FROM orders o
                    JOIN users u ON o.user_id = u.user_id
                    JOIN order_items oi ON o.order_id = oi.order_id
                    JOIN products p ON oi.product_id = p.product_id
                    GROUP BY o.order_id
                    ORDER BY o.created_at DESC
                """)
            else:
                # Regular users only see their own orders
                cur.execute("""
                    SELECT o.*,
                           GROUP_CONCAT(p.name || ' (x' || oi.quantity || ')') as product_names
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
        flash(f"Error loading orders: {str(e)}", 'danger')
        return render_template(template, orders=[])
