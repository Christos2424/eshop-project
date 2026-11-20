from flask import Blueprint, abort, request, redirect, url_for, session, flash, current_app

from ..db import get_cursor
from ..i18n import gettext as _
from ..security import login_required, rate_limit
from ..validators import validate_review_data

bp = Blueprint('reviews', __name__)

# Orders that count for the "Verified purchase" badge
PURCHASED_SQL = """
    EXISTS (SELECT 1 FROM order_items oi JOIN orders o ON o.order_id = oi.order_id
            WHERE oi.product_id = reviews.product_id AND o.user_id = reviews.user_id
            AND o.status != 'cancelled')
"""


def load_reviews(product_id):
    """Reviews of a product for its page: the newest first, the rating summary
    and the signed-in user's own review (None if they haven't written one)"""
    with get_cursor() as cur:
        cur.execute(f"""
            SELECT reviews.*, users.username, {PURCHASED_SQL} AS verified
            FROM reviews JOIN users ON users.user_id = reviews.user_id
            WHERE reviews.product_id = ?
            ORDER BY reviews.created_at DESC, reviews.review_id DESC
        """, (product_id,))
        reviews = cur.fetchall()

    count = len(reviews)
    counts = {stars: 0 for stars in range(5, 0, -1)}
    for review in reviews:
        counts[review['rating']] += 1

    summary = {
        'count': count,
        'average': round(sum(r['rating'] for r in reviews) / count, 1) if count else 0,
        # Rows for the rating bars, 5 stars first
        'breakdown': [{'stars': stars, 'count': n, 'percent': round(n * 100 / count) if count else 0}
                      for stars, n in counts.items()],
    }

    user_id = session.get('user_id')
    own_review = next((r for r in reviews if r['user_id'] == user_id), None)
    return reviews, summary, own_review


def product_page(product_id):
    return url_for('main.product_detail', product_id=product_id, _anchor='reviews')


@bp.route('/product/<int:product_id>/review', methods=['POST'])
@login_required
def save_review(product_id):
    """Write a review, or update the one this user already wrote for the product"""
    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM products WHERE product_id = ?", (product_id,))
        if not cur.fetchone():
            abort(404)

    errors = validate_review_data(request.form)
    if errors:
        for error in errors:
            flash(_(error), 'danger')
        return redirect(product_page(product_id))

    if not rate_limit(f"review:{session['user_id']}", max_attempts=10, window=3600):
        flash(_('Too many reviews in a short time. Please try again later.'), 'warning')
        return redirect(product_page(product_id))

    rating = int(request.form['rating'])
    title = request.form.get('title', '').strip() or None
    body = request.form['body'].strip()

    try:
        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO reviews (product_id, user_id, rating, title, body) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(product_id, user_id) DO UPDATE SET
                    rating = excluded.rating, title = excluded.title, body = excluded.body,
                    updated_at = CURRENT_TIMESTAMP
            """, (product_id, session['user_id'], rating, title, body))
        flash(_('Thanks! Your review has been saved.'), 'success')
    except Exception:
        current_app.logger.exception('Saving review for product %s failed', product_id)
        flash(_('An unexpected error occurred. Please try again.'), 'danger')

    return redirect(product_page(product_id))


@bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    """Authors can delete their own review; admins can delete any review"""
    with get_cursor() as cur:
        cur.execute("SELECT product_id, user_id FROM reviews WHERE review_id = ?", (review_id,))
        review = cur.fetchone()
        if not review:
            abort(404)
        if review['user_id'] != session['user_id'] and session.get('role') != 'admin':
            abort(403)
        cur.execute("DELETE FROM reviews WHERE review_id = ?", (review_id,))

    flash(_('Review deleted.'), 'success')
    return redirect(product_page(review['product_id']))
