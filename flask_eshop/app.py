from flask import Flask, render_template, request, redirect, url_for, session, flash, g, jsonify, send_from_directory
import sqlite3
import bcrypt
import os
import urllib.request
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from contextlib import contextmanager
import uuid
import re
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
DATABASE = 'eshop.db'

# Image upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Rate limiting storage
login_attempts = {}

@app.context_processor
def utility_processor():
    def get_image_url(image_url):
        if not image_url:
            return url_for('static', filename='images/placeholder.png')
        
        # If it starts with uploads/, it's a local file
        if image_url.startswith('uploads/'):
            return url_for('static', filename=image_url)
        
        # Otherwise, it's an external URL
        return image_url
    
    # Get categories for header dropdown
    categories = []
    try:
        with get_cursor() as cur:
            cur.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category")
            categories = [row[0] for row in cur.fetchall()]
    except:
        pass
    
    return dict(get_image_url=get_image_url, global_categories=categories)

# Ensure upload directory exists when module is imported
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at the end of request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@contextmanager
def get_cursor():
    """Context manager for database cursor"""
    db = get_db()
    cursor = db.cursor()
    try:
        yield cursor
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def download_image_from_url(url, product_id):
    """Download image from URL and save it locally"""
    try:
        # Validate URL
        parsed_url = urlparse(url)
        if not parsed_url.scheme in ['http', 'https']:
            return None
        
        # Get file extension from URL
        path = parsed_url.path
        ext = path.rsplit('.', 1)[-1].lower() if '.' in path else 'jpg'
        if ext not in ALLOWED_EXTENSIONS:
            ext = 'jpg'
        
        # Generate unique filename
        filename = f"product_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Download and save image
        urllib.request.urlretrieve(url, filepath)
        
        return f"uploads/{filename}"
    except Exception as e:
        print(f"Error downloading image from URL: {e}")
        return None

def save_uploaded_file(file, product_id):
    """Save uploaded file to the uploads folder"""
    try:
        if file and file.filename != '' and allowed_file(file.filename):
            # Check file size
            file.seek(0, os.SEEK_END)
            file_length = file.tell()
            file.seek(0)
            
            if file_length > app.config['MAX_CONTENT_LENGTH']:
                raise ValueError("File too large (max 16MB)")
            
            # Generate secure filename with unique identifier
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"product_{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
            filename = secure_filename(filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure upload directory exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save file
            file.save(filepath)
            return f"uploads/{filename}"
        return None
    except Exception as e:
        flash(f"Error processing image: {str(e)}", "danger")
        return None

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

# Validation functions
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    return len(password) >= 6

def validate_product_data(data):
    errors = []
    
    if len(data.get('name', '').strip()) < 2:
        errors.append("Product name must be at least 2 characters")
    
    try:
        price = float(data.get('price', 0))
        if price < 0:  # Changed from <= 0 to < 0 to allow free products
            errors.append("Price cannot be negative")
    except (ValueError, TypeError):
        errors.append("Price must be a valid number")
    
    try:
        stock = int(data.get('stock', 0))
        if stock < 0:  # Allow 0 stock
            errors.append("Stock cannot be negative")
    except (ValueError, TypeError):
        errors.append("Stock must be a valid integer")
    
    if len(data.get('description', '').strip()) < 10:
        errors.append("Description must be at least 10 characters")
    
    return errors

def validate_user_data(data):
    errors = []
    
    username = data.get('username', '').strip()
    if len(username) < 3:
        errors.append("Username must be at least 3 characters")
    if not username.isalnum():
        errors.append("Username can only contain letters and numbers")
    
    email = data.get('email', '').strip()
    if not validate_email(email):
        errors.append("Invalid email address")
    
    password = data.get('password', '')
    if not validate_password(password):
        errors.append("Password must be at least 6 characters")
    
    if password != data.get('confirm_password', ''):
        errors.append("Passwords do not match")
    
    return errors

# Decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(key, max_attempts=5, window=900):  # 15 minutes
    """Simple rate limiting"""
    current_time = time.time()
    if key not in login_attempts:
        login_attempts[key] = []
    
    # Remove old attempts
    login_attempts[key] = [attempt_time for attempt_time in login_attempts[key] 
                          if current_time - attempt_time < window]
    
    if len(login_attempts[key]) >= max_attempts:
        return False
    
    login_attempts[key].append(current_time)
    return True

def init_db():
    """Initialize the database with required tables and sample data"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role TEXT CHECK(role IN ('customer','admin')) DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products(
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            category VARCHAR(50),
            image_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders(
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total DECIMAL(10, 2) NOT NULL,
            status TEXT CHECK(status IN ('pending','paid','shipped','cancelled')) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Create order_items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items(
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_purchase DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_stock ON products(stock_quantity)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id)')
    
    # Create admin user if it doesn't exist
    admin_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, email, password_hash, role) 
        VALUES (?, ?, ?, ?)
    ''', ('admin', 'admin@eshop.com', admin_password, 'admin'))
    
    # Check if products table is empty and insert sample data
    cursor.execute("SELECT COUNT(*) as count FROM products")
    result = cursor.fetchone()
    if result[0] == 0:
        # Insert sample products
        sample_products = [
            ('Laptop', 'High-performance laptop with 16GB RAM and 512GB SSD', 999.99, 10, 'Electronics', None),
            ('Wireless Mouse', 'Ergonomic wireless mouse with long battery life', 29.99, 50, 'Electronics', None),
            ('Mechanical Keyboard', 'RGB mechanical keyboard with blue switches', 79.99, 25, 'Electronics', None),
            ('Headphones', 'Noise-cancelling Bluetooth headphones', 199.99, 15, 'Electronics', None),
            ('Smartphone', 'Latest smartphone with high-resolution camera', 699.99, 30, 'Electronics', None),
            ('Tablet', '10-inch tablet with stylus support', 399.99, 20, 'Electronics', None),
        ]
        
        cursor.executemany('''
            INSERT INTO products (name, description, price, stock_quantity, category, image_url)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', sample_products)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Favicon route to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    try:
        return send_from_directory(os.path.join(app.root_path, 'static', 'images'),
                                 'favicon.ico', 
                                 mimetype='image/vnd.microsoft.icon')
    except:
        # If favicon doesn't exist, return empty response
        return '', 204
    
@app.route("/")
def home():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '')
    category = request.args.get('category', '')
    stock_filter = request.args.get('stock', 'all')  # 'all', 'in_stock', 'out_of_stock'
    sort_by = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    per_page = 12
    
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
                    conditions.append("price >= ?")
                    params.append(float(min_price))
                except ValueError:
                    pass
            
            if max_price:
                try:
                    conditions.append("price <= ?")
                    params.append(float(max_price))
                except ValueError:
                    pass
            
            if conditions:
                where_clause = " WHERE " + " AND ".join(conditions)
                query += where_clause
                count_query += where_clause
            
            # Get total count
            cur.execute(count_query, params)
            total = cur.fetchone()[0]
            
            # Add sorting
            sort_map = {
                'newest': 'created_at DESC',
                'oldest': 'created_at ASC',
                'price_low': 'price ASC',
                'price_high': 'price DESC',
                'name_az': 'name ASC',
                'name_za': 'name DESC'
            }
            sort_clause = sort_map.get(sort_by, 'created_at DESC')
            
            # Get products with pagination
            query += f" ORDER BY {sort_clause} LIMIT ? OFFSET ?"
            params.extend([per_page, (page-1)*per_page])
            cur.execute(query, params)
            products = cur.fetchall()
            
            # Get distinct categories for filter
            cur.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category")
            categories = [row[0] for row in cur.fetchall()]
            
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
    
@app.route('/search')
def search():
    query = request.args.get('q', '')
    stock_filter = request.args.get('stock', 'all')
    sort_by = request.args.get('sort', 'newest')
    min_price = request.args.get('min_price', '')
    max_price = request.args.get('max_price', '')
    
    if query:
        return redirect(url_for('home', q=query, stock=stock_filter, sort=sort_by, 
                               min_price=min_price, max_price=max_price))
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate user data
        validation_errors = validate_user_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('register.html')
        
        try:
            with get_cursor() as cur:
                # Check if user exists
                cur.execute('SELECT * FROM users WHERE email = ?', (email,))
                if cur.fetchone():
                    flash('Email already registered!', 'danger')
                    return render_template('register.html')
                
                cur.execute('SELECT * FROM users WHERE username = ?', (username,))
                if cur.fetchone():
                    flash('Username already taken!', 'danger')
                    return render_template('register.html')
                
                hashed_pw = hash_password(password)
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, hashed_pw)
                )
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            flash(f"Registration error: {str(e)}", 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        next_page = request.form.get('next') or request.args.get('next')
        
        # Rate limiting
        if not rate_limit(email):
            flash('Too many login attempts. Please try again in 15 minutes.', 'danger')
            return render_template('login.html')
        
        try:
            with get_cursor() as cur:
                cur.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = cur.fetchone()
            
            if user and check_password(user['password_hash'], password):
                session["user_id"] = user['user_id']
                session["username"] = user['username']
                session["role"] = user['role']
                flash('Login successful!', 'success')
                
                # Clear rate limiting for successful login
                if email in login_attempts:
                    del login_attempts[email]
                
                # Redirect to the requested page or home
                return redirect(next_page or url_for('home'))
            else:
                flash('Invalid email or password', 'danger')
                return render_template('login.html')
    
        except Exception as e:
            flash(f"Login error: {str(e)}", 'danger')
            return render_template("login.html")
    
    # GET request - show login form
    next_page = request.args.get('next', '')
    return render_template('login.html', next=next_page)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')        
    return redirect(url_for('home'))

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('home'))
        
        return render_template('product.html', product=product)
    
    except Exception as e:
        flash(f"Error loading product: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    if not product_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid product'})
        flash('Invalid product', 'danger')
        return redirect(request.referrer or url_for('home'))
    
    try:
        # Validate product exists
        with get_cursor() as cur:
            cur.execute("SELECT product_id, name, stock_quantity FROM products WHERE product_id = ?", (product_id,))
            product = cur.fetchone()
            
            if not product:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': 'Product not found'})
                flash('Product not found', 'danger')
                return redirect(request.referrer or url_for('home'))
            
            # FIXED: Check stock availability - fix the logic order
            if product['stock_quantity'] == 0:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': f"{product['name']} is out of stock"})
                flash(f"{product['name']} is currently out of stock", 'warning')
                return redirect(request.referrer or url_for('home'))
            
            # Check if requested quantity exceeds available stock
            if product['stock_quantity'] < quantity:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': f"Only {product['stock_quantity']} units available"})
                flash(f"Only {product['stock_quantity']} units of {product['name']} available", 'warning')
                return redirect(request.referrer or url_for('home'))
        
        # Update cart
        if 'cart' not in session:
            session["cart"] = {}
        
        cart = session['cart']
        current_quantity = cart.get(str(product_id), 0)
        new_quantity = current_quantity + quantity
        
        # Final check to ensure we don't exceed stock
        if new_quantity > product['stock_quantity']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': f"Cannot add more than {product['stock_quantity']} units"})
            flash(f"Cannot add more than {product['stock_quantity']} units of {product['name']}", 'warning')
            return redirect(request.referrer or url_for('home'))
        
        cart[str(product_id)] = new_quantity
        session["cart"] = cart
        session.modified = True
        
        # Calculate total cart count for response
        total_cart_count = sum(cart.values())
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': f"{product['name']} added to cart!",
                'cart_count': total_cart_count
            })
        
        flash("Item added to cart!", "success")
        return redirect(request.referrer or url_for('home'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f"Error: {str(e)}"})
        flash(f"Error adding to cart: {str(e)}", 'danger')
        return redirect(request.referrer or url_for('home'))

@app.route('/update_cart', methods=['POST'])
def update_cart():
    product_id = request.form.get('product_id')
    quantity = request.form.get('quantity')
    
    if not product_id or not quantity:
        flash('Invalid request', 'danger')
        return redirect(url_for('view_cart'))
    
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
                    return redirect(url_for('view_cart'))
                
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
    
    return redirect(url_for('view_cart'))

@app.route("/cart")
def view_cart():
    if "cart" not in session or not session["cart"]:
        return render_template("cart.html", cart_items=[], total=0)
    
    try:
        cart = session["cart"]
        product_ids = list(cart.keys())
        
        if not product_ids:
            return render_template('cart.html', cart_items=[], total=0)
        
        placeholders = ','.join(['?'] * len(product_ids))
        
        with get_cursor() as cur:
            cur.execute(
                f"SELECT * FROM products WHERE product_id IN ({placeholders})",
                product_ids
            )
            products = cur.fetchall()
        
        cart_items = []
        total = 0
        items_to_remove = []
        
        for product in products:
            pid = str(product["product_id"])
            qty = cart[pid]  
            item_total = product["price"] * qty
            cart_items.append({
                "product": product,
                "quantity": qty,
                "total": item_total
            })      
            total += item_total
        
        # Remove any products from cart that weren't found in database
        found_ids = [str(product["product_id"]) for product in products]
        for pid in cart.keys():
            if pid not in found_ids:
                items_to_remove.append(pid)
        
        for pid in items_to_remove:
            del cart[pid]
        
        if items_to_remove:
            session["cart"] = cart
            session.modified = True
            flash("Some items in your cart are no longer available and have been removed.", "warning")
        
        return render_template("cart.html", cart_items=cart_items, total=total)
    
    except Exception as e:
        flash(f"Error loading cart: {str(e)}", "danger")
        # If there's an error, clear the cart to prevent further issues
        session.pop('cart', None)
        return render_template("cart.html", cart_items=[], total=0)

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'cart' in session and 'product_id' in request.form:
        product_id = request.form['product_id']
        cart = session['cart']
        if str(product_id) in cart:
            del cart[str(product_id)]
            session['cart'] = cart
            session.modified = True
            flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))

@app.route("/checkout", methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'GET':
        # Show checkout page for logged-in users
        if "cart" not in session or not session["cart"]:
            flash("Your cart is empty", 'warning')
            return redirect(url_for("view_cart"))
        
        # Calculate total for display
        cart = session["cart"]
        product_ids = list(cart.keys())
        
        if not product_ids:
            return redirect(url_for("view_cart"))
        
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
            pid = str(product["product_id"])
            qty = cart[pid]  
            item_total = product["price"] * qty
            cart_items.append({
                "product": product,
                "quantity": qty,
                "total": item_total
            })      
            total += item_total
        
        return render_template('checkout.html', cart_items=cart_items, total=total)
    
    # POST request - process the actual checkout
    if "cart" not in session or not session["cart"]:
        flash("Your cart is empty", 'warning')
        return redirect(url_for("view_cart"))
    
    try:
        user_id = session["user_id"]
        cart = session["cart"]
        product_ids = [int(pid) for pid in cart.keys()]
        
        if not product_ids:
            flash("Your cart is empty", 'warning')
            return redirect(url_for("view_cart"))
        
        db = get_db()
        db.execute("BEGIN TRANSACTION")
        
        try:
            cur = db.cursor()
            placeholders = ','.join(['?'] * len(product_ids))
            
            # Get product details with row locking
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
                    flash(f"Product ID {pid} no longer available", 'danger')
                    return redirect(url_for('view_cart'))
                    
                product = products[pid]
                if product['stock_quantity'] < qty:
                    insufficient_stock.append(f"{product['name']} (available: {product['stock_quantity']})")
                total += product['price'] * qty
            
            if insufficient_stock:
                flash(f"Insufficient stock for: {', '.join(insufficient_stock)}", 'danger')
                db.rollback()
                return redirect(url_for('view_cart'))
            
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
                # Update stock
                cur.execute(
                    "UPDATE products SET stock_quantity = stock_quantity - ? WHERE product_id = ?",
                    (qty, int(pid))
                )
            
            db.commit()
            
            # Clear cart
            session.pop('cart', None)
            session.modified = True
            
            flash(f'Order #{order_id} placed successfully!', 'success')
            return redirect(url_for('user_orders'))
            
        except Exception as e:
            db.rollback()
            raise e
            
    except Exception as e:
        flash(f"Checkout failed: {str(e)}", 'danger')
        return redirect(url_for('view_cart'))

@app.route('/orders')
@login_required
def user_orders():
    try:
        with get_cursor() as cur:
            if session['role'] == 'admin':
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
                orders = cur.fetchall()
                return render_template('admin_orders.html', orders=orders)
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
                return render_template('user_orders.html', orders=orders)
    except Exception as e:
        flash(f"Error loading orders: {str(e)}", 'danger')
        # Return appropriate template based on role
        if session.get('role') == 'admin':
            return render_template('admin_orders.html', orders=[])
        else:
            return render_template('user_orders.html', orders=[])


@app.route('/admin/products')
@admin_required
def admin_products():
    try:
        with get_cursor() as cur:
            # Fetch products
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
            
        return render_template('admin_products.html', products=products, orders=orders)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():
    if request.method == 'POST':
        # Validate product data
        validation_errors = validate_product_data(request.form)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('add_product.html')
        
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        image_url = request.form.get('image_url', '').strip()
        
        image_path = None
        
        try:
            # Handle image upload or URL
            if 'image_file' in request.files:
                file = request.files['image_file']
                if file and file.filename != '':
                    # Generate a temporary product_id for the filename
                    with get_cursor() as cur:
                        cur.execute("SELECT COALESCE(MAX(product_id), 0) + 1 as next_id FROM products")
                        next_id = cur.fetchone()['next_id']
                    
                    image_path = save_uploaded_file(file, next_id)
                    if image_path:
                        flash('Image uploaded successfully!', 'success')
            
            # If no file uploaded but URL provided
            if not image_path and image_url:
                with get_cursor() as cur:
                    cur.execute("SELECT COALESCE(MAX(product_id), 0) + 1 as next_id FROM products")
                    next_id = cur.fetchone()['next_id']
                
                image_path = download_image_from_url(image_url, next_id)
                if image_path:
                    flash('Image downloaded from URL successfully!', 'success')
                else:
                    flash('Failed to download image from URL', 'warning')
            
            with get_cursor() as cur:
                cur.execute(
                    """INSERT INTO products 
                    (name, description, price, stock_quantity, category, image_url)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (name, description, price, stock, category, image_path)
                )
            
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            flash(f"Error adding product: {str(e)}", 'danger')
            return render_template('add_product.html')
    
    return render_template('add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    try:
        with get_cursor() as cur:
            if request.method == 'POST':
                # Validate product data
                validation_errors = validate_product_data(request.form)
                if validation_errors:
                    for error in validation_errors:
                        flash(error, 'danger')
                    return redirect(url_for('edit_product', product_id=product_id))
                
                name = request.form['name']
                description = request.form['description']
                price = float(request.form['price'])
                stock = int(request.form['stock'])
                category = request.form['category']
                image_url = request.form.get('image_url', '').strip()
                
                # Get current product data
                cur.execute("SELECT image_url FROM products WHERE product_id = ?", (product_id,))
                current_product = cur.fetchone()
                current_image = current_product['image_url'] if current_product else None
                
                image_path = current_image  # Keep current image by default
                
                # Handle image upload
                if 'image_file' in request.files:
                    file = request.files['image_file']
                    if file and file.filename != '':
                        new_image_path = save_uploaded_file(file, product_id)
                        if new_image_path:
                            image_path = new_image_path
                            flash('New image uploaded successfully!', 'success')
                
                # Handle image URL
                if not image_path and image_url:
                    new_image_path = download_image_from_url(image_url, product_id)
                    if new_image_path:
                        image_path = new_image_path
                        flash('New image downloaded from URL successfully!', 'success')
                    else:
                        flash('Failed to download image from URL', 'warning')
                
                # If "remove image" is checked, set image_path to None
                if request.form.get('remove_image'):
                    image_path = None
                    flash('Image removed successfully!', 'success')
                
                cur.execute(
                    """UPDATE products 
                    SET name=?, description=?, price=?, stock_quantity=?, category=?, image_url=?
                    WHERE product_id=?""",
                    (name, description, price, stock, category, image_path, product_id)
                )
                flash('Product updated successfully!', 'success')
                return redirect(url_for('admin_products'))
            else:
                cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
                product = cur.fetchone()
                if not product:
                    flash('Product not found', 'danger')
                    return redirect(url_for('admin_products'))
                return render_template('edit_product.html', product=product)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    try:
        with get_cursor() as cur:
            # Check if product exists in any orders
            cur.execute("""
                SELECT COUNT(*) FROM order_items 
                WHERE product_id = ?
            """, (product_id,))
            order_count = cur.fetchone()[0]
            
            if order_count > 0:
                flash('Cannot delete product that has been ordered. Consider archiving instead.', 'danger')
            else:
                cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
                flash('Product deleted successfully!', 'success')
    except Exception as e:
        flash(f"Error deleting product: {str(e)}", 'danger')
    
    return redirect(url_for('admin_products'))

# Add this route for admin order status updates
@app.route('/admin/update_order/<int:order_id>', methods=['POST'])
@admin_required
def update_order_status(order_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'paid', 'shipped', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status'})
        
        with get_cursor() as cur:
            cur.execute(
                "UPDATE orders SET status = ? WHERE order_id = ?",
                (new_status, order_id)
            )
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(error):
    flash('File too large. Maximum size is 16MB.', 'danger')
    return redirect(request.referrer or url_for('home'))

@app.errorhandler(Exception)
def handle_exception(error):
    flash('An unexpected error occurred. Please try again.', 'danger')
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    if not os.path.exists(DATABASE):
        init_db()
        print("Database created successfully!")
    else:
        # Always ensure tables exist
        init_db()
    
    # Ensure upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"Upload folder created: {UPLOAD_FOLDER}")
    
    app.run(debug=True)