from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import bcrypt
import os
import urllib.request
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from contextlib import contextmanager
import uuid
 
 
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database configuration
DATABASE = 'eshop.db'

# Image upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

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
    
    return dict(get_image_url=get_image_url)
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
    if file and file.filename != '' and allowed_file(file.filename):
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

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(hashed_password, user_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(user_password.encode('utf-8'), hashed_password)

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

@app.route("/")
def home():
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products WHERE stock_quantity > 0")
            products = cur.fetchall()
        return render_template('index.html', products=products)
    except Exception as e:
        flash(f"Database error: {str(e)}", 'danger')
        return render_template('index.html', products=[])
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))
        
        try:
            with get_cursor() as cur:
                # Check if user exists
                cur.execute('SELECT * FROM users WHERE email = ?', (email,))
                if cur.fetchone():
                    flash('Email already registered!', 'danger')
                    return redirect(url_for('register'))
                
                hashed_pw = hash_password(password)
                cur.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, hashed_pw)
                )
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        next_page = request.form.get('next') or request.args.get('next')
        
        try:
            with get_cursor() as cur:
                cur.execute('SELECT * FROM users WHERE email = ?', (email,))
                user = cur.fetchone()
            
            if user and check_password(user['password_hash'], password):
                session["user_id"] = user['user_id']
                session["username"] = user['username']
                session["role"] = user['role']
                flash('Login successful!', 'success')
                
                # Redirect to the requested page or home
                return redirect(next_page or url_for('home'))
            else:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))
    
        except Exception as e:
            flash(f"Database error: {str(e)}", 'danger')
            return redirect(url_for("login"))
    
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
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    # No login required to add to cart
    product_id = request.form['product_id']
    quantity = int(request.form.get('quantity', 1))
    
    try:
        if 'cart' not in session:
            session["cart"] = {}
        
        cart = session['cart']
        cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
        session["cart"] = cart
        session.modified = True
        
        flash("Item added to cart!", "success")
        return redirect(request.referrer or url_for('home'))
        
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(request.referrer or url_for('home'))

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
        
        return render_template("cart.html", cart_items=cart_items, total=total)
    
    except Exception as e:
        flash(f"Error loading cart: {str(e)}", "danger")
        return render_template("cart.html", cart_items=[], total=0)

@app.route("/checkout", methods=['GET', 'POST'])
def checkout():
    # Only require login when actually trying to checkout
    if "user_id" not in session:
        flash('Please log in to complete your purchase', 'warning')
        return redirect(url_for('login'))
    
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
            
            # Get product details
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
                    insufficient_stock.append(product['name'])
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
            return redirect(url_for('home'))
            
        except Exception as e:
            db.rollback()
            raise e
            
    except Exception as e:
        flash(f"Checkout failed: {str(e)}", 'danger')
        return redirect(url_for('view_cart'))

@app.route('/admin/products')
def admin_products():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        with get_cursor() as cur:
            cur.execute("SELECT * FROM products")
            products = cur.fetchall()
        return render_template('admin_products.html', products=products)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
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
            flash(f"Error: {str(e)}", 'danger')
            return render_template('add_product.html')
    
    return render_template('add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        with get_cursor() as cur:
            if request.method == 'POST':
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
def delete_product(product_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        with get_cursor() as cur:
            cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
    
    return redirect(url_for('admin_products'))

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