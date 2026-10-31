from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from ..db import get_cursor, get_categories

bp = Blueprint('main', __name__)

SORT_MAP = {
    'newest': 'created_at DESC',
    'oldest': 'created_at ASC',
    'price_low': 'price ASC',
    'price_high': 'price DESC',
    'name_az': 'name ASC',
    'name_za': 'name DESC'
}


@bp.route("/")
def home():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    category = request.args.get('category', '')
    stock_filter = request.args.get('stock', 'all')  # 'all', 'in_stock', 'out_of_stock'
    sort_by = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    per_page = current_app.config['PRODUCTS_PER_PAGE']

    try:
        with get_cursor() as cur:
            # Build query based on filters
            query = "SELECT * FROM products"
            count_query = "SELECT COUNT(*) FROM products"
            params = []
            conditions = []

            if search_query:
                conditions.append("name LIKE ?")
                params.append(f'%{search_query}%')

            if category:
                conditions.append("category = ?")
                params.append(category)

            # Stock filter
            if stock_filter == 'in_stock':
                conditions.append("stock_quantity > 0")
            elif stock_filter == 'out_of_stock':
                conditions.append("stock_quantity = 0")
            # 'all' shows everything, so no condition needed

            # Price range filtering
            if min_price:
                try:
                    params.append(float(min_price))
                    conditions.append("price >= ?")
                except ValueError:
                    pass

            if max_price:
                try:
                    params.append(float(max_price))
                    conditions.append("price <= ?")
                except ValueError:
                    pass

            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
                query += where_clause
                count_query += where_clause

            # Get total count
            cur.execute(count_query, params)
            total = cur.fetchone()[0]

            # Get products with pagination
            sort_clause = SORT_MAP.get(sort_by, 'created_at DESC')
            query += f" ORDER BY {sort_clause} LIMIT ? OFFSET ?"
            params.extend([per_page, (page-1)*per_page])
            cur.execute(query, params)
            products = cur.fetchall()

        # Get distinct categories for filter
        categories = get_categories()
        total_pages = (total + per_page - 1) // per_page

        return render_template('index.html',
                               products=products,
                               page=page,
                               per_page=per_page,
                               total=total,
                               total_pages=total_pages,
                               search_query=search_query,
                               category=category,
                               categories=categories,
                               stock_filter=stock_filter,
                               sort_by=sort_by,
                               min_price=min_price,
                               max_price=max_price)
    except Exception as e:
        flash(f"Error loading products: {str(e)}", 'danger')
        return render_template('index.html', products=[], page=1, total=0, total_pages=0, categories=[])


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
            flash('Product not found', 'danger')
            return redirect(url_for('main.home'))

        return render_template('product.html', product=product)

    except Exception as e:
        flash(f"Error loading product: {str(e)}", 'danger')
        return redirect(url_for('main.home'))
