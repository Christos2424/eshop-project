from flask import Blueprint, request, jsonify, url_for, current_app

from ..db import RATING_COLUMNS, get_cursor
from ..i18n import fold, name_sql
from ..utils import product_to_dict
from .main import LIKE_ESCAPE, escape_like, search_condition

bp = Blueprint('api', __name__, url_prefix='/api')

MAX_PRODUCT_IDS = 24


@bp.route('/search')
def search():
    """Live search suggestions for the header search box"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'query': query, 'total': 0, 'results': []})

    condition, params = search_condition(query)
    with get_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM products WHERE {condition}", params)
        total = cur.fetchone()[0]

        # Names that start with the query first, then products that are in stock
        name = name_sql()
        cur.execute(f"""
            SELECT * FROM products WHERE {condition}
            ORDER BY (fold({name}) LIKE ? {LIKE_ESCAPE}) DESC, stock_quantity > 0 DESC, {name}
            LIMIT ?
        """, params + [f'{escape_like(fold(query))}%', current_app.config['SEARCH_SUGGESTIONS']])
        products = cur.fetchall()

    return jsonify({
        'query': query,
        'total': total,
        'results': [product_to_dict(product) for product in products],
        'url': url_for('main.home', q=query),
    })


@bp.route('/products')
def products():
    """Products by id (?ids=3,1,7), in the order given; used for saved and recently viewed items"""
    ids = [int(pid) for pid in request.args.get('ids', '').split(',') if pid.strip().isdigit()]
    ids = list(dict.fromkeys(ids))[:MAX_PRODUCT_IDS]
    if not ids:
        return jsonify({'products': []})

    placeholders = ','.join(['?'] * len(ids))
    with get_cursor() as cur:
        cur.execute(f"SELECT *, {RATING_COLUMNS} FROM products WHERE product_id IN ({placeholders})", ids)
        by_id = {product['product_id']: product for product in cur.fetchall()}

    return jsonify({'products': [product_to_dict(by_id[pid]) for pid in ids if pid in by_id]})
