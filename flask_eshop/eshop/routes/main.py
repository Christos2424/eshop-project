import json

from flask import Blueprint, abort, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.exceptions import HTTPException

from ..db import RATING_COLUMNS, get_cursor, get_categories
from ..i18n import LANGUAGES, catalogs, category_label, fold, gettext as _, name_sql
from ..utils import is_ajax, is_safe_redirect
from .reviews import load_reviews

bp = Blueprint('main', __name__)

# {name} is replaced by the product name column for the current language;
# fold() makes A-Z ignore case and Greek accents
SORT_MAP = {
    'newest': 'created_at DESC',
    'oldest': 'created_at ASC',
    'price_low': 'price ASC',
    'price_high': 'price DESC',
    'name_az': 'fold({name}) ASC',
    'name_za': 'fold({name}) DESC',
    'top_rated': 'rating DESC, review_count DESC'
}

# Filter values that mean "no filter", left out of URLs
FILTER_DEFAULTS = {'q': '', 'category': '', 'stock': 'all', 'sort': 'newest', 'min_price': '', 'max_price': ''}

STOCK_LABELS = {'in_stock': 'In stock', 'out_of_stock': 'Out of stock'}


LIKE_ESCAPE = "ESCAPE '\\'"


def escape_like(text):
    """Make % and _ in a search match themselves instead of acting as LIKE wildcards"""
    return text.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def search_condition(query):
    """SQL condition and params matching a search box query against the English and Greek
    names and the category (in either language), ignoring case and accents"""
    folded = fold(query)
    like = f'%{escape_like(folded)}%'
    conditions = [f"fold(name) LIKE ? {LIKE_ESCAPE}", f"fold(name_el) LIKE ? {LIKE_ESCAPE}",
                  f"fold(category) LIKE ? {LIKE_ESCAPE}"]
    params = [like, like, like]

    # Categories are stored in English: also match their translated names (e.g. 'βιβλ' finds Books)
    matching = [c for c in get_categories() if folded in fold(category_label(c))]
    if matching:
        conditions.append(f"category IN ({','.join('?' * len(matching))})")
        params.extend(matching)

    return "(" + " OR ".join(conditions) + ")", params


def read_filters(args):
    return {key: args.get(key, default).strip() for key, default in FILTER_DEFAULTS.items()}


def active_params(filters):
    """Only the filters that differ from their defaults, for building clean URLs"""
    return {key: value for key, value in filters.items() if value and value != FILTER_DEFAULTS[key]}


def filter_pills(filters):
    """Removable labels for the active filters, each with the URL that drops it"""
    labels = {
        'q': lambda v: _('Search: {query}', query=v),
        'category': category_label,
        'stock': lambda v: _(STOCK_LABELS[v]) if v in STOCK_LABELS else None,
        'min_price': lambda v: _('From €{price}', price=v),
        'max_price': lambda v: _('Up to €{price}', price=v),
    }
    params = active_params(filters)
    pills = []
    for key, label in labels.items():
        if key in params and label(params[key]):
            remaining = {k: v for k, v in params.items() if k != key}
            pills.append({'label': label(params[key]), 'url': url_for('main.home', **remaining)})
    return pills


def query_products(filters, page, per_page):
    """Return (products, total) for one page of products matching the filters"""
    conditions = []
    params = []

    if filters['q']:
        condition, search_params = search_condition(filters['q'])
        conditions.append(condition)
        params.extend(search_params)

    if filters['category']:
        conditions.append("category = ?")
        params.append(filters['category'])

    # Stock filter; 'all' shows everything, so no condition needed
    if filters['stock'] == 'in_stock':
        conditions.append("stock_quantity > 0")
    elif filters['stock'] == 'out_of_stock':
        conditions.append("stock_quantity = 0")

    # Price range filtering
    for key, operator in (('min_price', '>='), ('max_price', '<=')):
        if filters[key]:
            try:
                params.append(float(filters[key]))
                conditions.append(f"price {operator} ?")
            except ValueError:
                pass

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    sort_clause = SORT_MAP.get(filters['sort'], 'created_at DESC').format(name=name_sql())

    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM products" + where_clause, params)
        total = cur.fetchone()[0]

        cur.execute(
            f"SELECT *, {RATING_COLUMNS} FROM products{where_clause} ORDER BY {sort_clause}, product_id DESC LIMIT ? OFFSET ?",
            params + [per_page, (page - 1) * per_page]
        )
        products = cur.fetchall()

    return products, total


@bp.route("/")
def home():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = current_app.config['PRODUCTS_PER_PAGE']
    filters = read_filters(request.args)

    context = dict(filters=filters, filter_params=active_params(filters), pills=filter_pills(filters),
                   page=page, products=[], total=0, total_pages=0, store_total=0)

    try:
        products, total = query_products(filters, page, per_page)
        context.update(products=products, total=total, total_pages=(total + per_page - 1) // per_page)

        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM products")
            context['store_total'] = cur.fetchone()[0]
    except Exception:
        current_app.logger.exception('Loading products failed')
        flash(_('An unexpected error occurred. Please try again.'), 'danger')

    # The shop page's JavaScript fetches only the results block when filters change
    if is_ajax():
        return render_template('shop/_results.html', **context)
    return render_template('shop/index.html', **context)


@bp.route('/search')
def search():
    query = request.args.get('q', '')
    stock_filter = request.args.get('stock', 'all')
    sort_by = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')

    if query:
        return redirect(url_for('main.home', q=query, stock=stock_filter, sort=sort_by,
                                min_price=min_price, max_price=max_price))
    return redirect(url_for('main.home'))


@bp.route("/product/<int:product_id>")
def product_detail(product_id):
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()

            if not product:
                abort(404)

            # Suggest products from the same category first, then the newest others
            cur.execute(f"""
                SELECT *, {RATING_COLUMNS} FROM products WHERE product_id != ?
                ORDER BY (category = ?) DESC, stock_quantity > 0 DESC, created_at DESC
                LIMIT 4
            """, (product_id, product['category']))
            related = cur.fetchall()

        reviews, review_summary, own_review = load_reviews(product_id)
        return render_template('shop/product.html', product=product, related=related,
                               reviews=reviews, review_summary=review_summary, own_review=own_review)

    except HTTPException:
        raise
    except Exception:
        current_app.logger.exception('Loading product %s failed', product_id)
        flash(_('An unexpected error occurred. Please try again.'), 'danger')
        return redirect(url_for('main.home'))


@bp.route('/language/<code>')
def set_language(code):
    """Switch language, then go back to the page the user was on"""
    if code in LANGUAGES:
        session['lang'] = code
    target = request.referrer
    if not is_safe_redirect(target):
        target = url_for('main.home')
    return redirect(target)


@bp.route('/i18n/<code>.js')
def translations_js(code):
    """Translations for the JavaScript t() function; cached by the browser (the URL has a version)"""
    catalog = catalogs.get(code, {}) if code in LANGUAGES else {}
    body = f"window.I18N = {json.dumps(catalog, ensure_ascii=False)};\n"
    response = current_app.response_class(body, mimetype='application/javascript')
    response.cache_control.public = True
    response.cache_control.max_age = 60 * 60 * 24 * 365
    return response
