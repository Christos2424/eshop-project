from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_mysqldb import MySQL 
import bcrypt
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = os.urandom(24)

# Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'eshop_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# File upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

# Create upload folder if not exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper functions
def hash_password(password):
    # Generate hash and decode to string for storage
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(hashed_password, user_password):
    # Encode both to bytes for comparison
    return bcrypt.checkpw(
        user_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route("/")
def home():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE stock_quantity > 0")
        products = cur.fetchall()
        cur.close()
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
            cur = mysql.connection.cursor()
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            if cur.fetchone():
                flash('Email already registered!', 'danger')
                return redirect(url_for('register'))
            
            hashed_pw = hash_password(password)
            cur.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, hashed_pw)
            )
            mysql.connection.commit()
            cur.close()
            
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        
        try: 
            cur = mysql.connection.cursor()
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            cur.close()
        
            if user and check_password(user['password_hash'], password):
                session["user_id"] = user['user_id']
                session["username"] = user['username']
                session["role"] = user['role']
                flash('Login successful!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))
    
        except Exception as e:
            flash(f"Database error: {str(e)}", 'danger')
            return redirect(url_for("login"))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')        
    return redirect(url_for('home'))

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
        product = cur.fetchone()
        cur.close()
        
        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('home'))
        
        return render_template('product.html', product=product)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))
    
    product_id = request.form['product_id']
    quantity = int(request.form.get('quantity', 1))
    
    try:
        if 'cart' not in session:
            session["cart"] = {}
        
        cart = session['cart']
        cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
        session["cart"] = cart
        
        flash("Item added to cart!", "success")
        return redirect(url_for('product_detail', product_id=product_id))
        
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route("/cart")
def view_cart():
    if "cart" not in session or not session["cart"]:
        return render_template("cart.html", cart_items=[], total=0)
    
    try:
        cart = session["cart"]
        product_ids = list(cart.keys())
        if not product_ids:
            return render_template('cart.html', cart_items=[], total=0)
        
        format_strings = ','.join(['%s'] * len(product_ids))
        
        cur = mysql.connection.cursor()
        cur.execute(
            f"SELECT * FROM products WHERE product_id IN ({format_strings})",
            tuple(product_ids)
        )
        products = cur.fetchall()
        cur.close()
        
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

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('view_cart'))
    
    product_id = request.form['product_id']
    cart = session['cart']
    
    if str(product_id) in cart:
        del cart[str(product_id)]
        session['cart'] = cart
        flash('Item removed from cart', 'success')
    
    return redirect(url_for('view_cart'))

@app.route("/checkout", methods=['POST'])
def checkout():
    if "user_id" not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))
    
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
        
        cur = mysql.connection.cursor()
        cur.execute("START TRANSACTION")
        
        format_strings = ",".join(['%s'] * len(product_ids))
        cur.execute(
            f"SELECT product_id, price, stock_quantity, name FROM products WHERE product_id IN ({format_strings}) FOR UPDATE",
            tuple(product_ids)
        )
        products = {str(p['product_id']): p for p in cur.fetchall()}
        
        total = 0
        insufficient_stock = []
        
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
            cur.execute("ROLLBACK")
            cur.close()
            return redirect(url_for('view_cart'))
        
        cur.execute(
            "INSERT INTO orders (user_id, total) VALUES (%s, %s)",
            (user_id, total)
        )
        order_id = cur.lastrowid
        
        for pid, qty in cart.items():
            product = products[pid]
            cur.execute(
                """INSERT INTO order_items 
                (order_id, product_id, quantity, price_at_purchase)
                VALUES (%s, %s, %s, %s)""",
                (order_id, int(pid), qty, product['price'])
            )
            cur.execute(
                "UPDATE products SET stock_quantity = stock_quantity - %s WHERE product_id = %s",
                (qty, int(pid))
            )
        
        mysql.connection.commit()
        cur.close()
        
        session.pop('cart', None)
        flash(f'Order #{order_id} placed successfully!', 'success')
        return redirect(url_for('home'))
        
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Checkout failed: {str(e)}", 'danger')
        return redirect(url_for('view_cart'))

@app.route('/orders')
def user_orders():
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('login'))
    
    try:
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT o.order_id, o.total, o.status, o.created_at,
                   GROUP_CONCAT(p.name SEPARATOR ', ') AS products
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            JOIN products p ON oi.product_id = p.product_id
            WHERE o.user_id = %s
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
        """, (user_id,))
        orders = cur.fetchall()
        cur.close()
        return render_template('orders.html', orders=orders)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('home'))

@app.route('/admin/products')
def admin_products():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products")
        products = cur.fetchall()
        cur.close()
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
        image = request.files['image']
        image_url = None

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            unique_filename = str(uuid.uuid4()) + '_' + filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image.save(image_path)
            image_url = unique_filename
        
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                """INSERT INTO products 
                (name, description, price, stock_quantity, category, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (name, description, price, stock, category, image_url)
            )
            mysql.connection.commit()
            cur.close()
            flash('Product added successfully!', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error: {str(e)}", 'danger')
            return render_template('add_product.html')
    
    return render_template('add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category = request.form['category']
        image = request.files['image']
        existing_image = request.form.get('existing_image')
        image_url = existing_image
        
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            unique_filename = str(uuid.uuid4()) + '_' + filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            image.save(image_path)
            image_url = unique_filename
        
        try:
            cur.execute(
                """UPDATE products SET 
                name=%s, description=%s, price=%s, 
                stock_quantity=%s, category=%s, image_url=%s
                WHERE product_id=%s""",
                (name, description, price, stock, category, image_url, product_id)
            )
            mysql.connection.commit()
            flash('Product updated!', 'success')
            return redirect(url_for('admin_products'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    cur.execute("SELECT * FROM products WHERE product_id=%s", (product_id,))
    product = cur.fetchone()
    cur.close()
    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM products WHERE product_id=%s", (product_id,))
        mysql.connection.commit()
        flash('Product deleted!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin_products'))

@app.route('/admin/orders')
def admin_orders():
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT o.order_id, u.username, o.total, o.status, o.created_at
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC
        """)
        orders = cur.fetchall()
        cur.close()
        return render_template('admin_orders.html', orders=orders)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('admin_products'))

@app.route('/admin/order/<int:order_id>')
def admin_order_detail(order_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    try:
        cur = mysql.connection.cursor()
        # Get order summary
        cur.execute("""
            SELECT o.*, u.username, u.email
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = %s
        """, (order_id,))
        order = cur.fetchone()
        
        if not order:
            flash('Order not found', 'danger')
            return redirect(url_for('admin_orders'))
        
        # Get order items
        cur.execute("""
            SELECT oi.*, p.name, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = %s
        """, (order_id,))
        items = cur.fetchall()
        cur.close()
        
        return render_template('admin_order_detail.html', order=order, items=items)
    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('admin_orders'))

@app.route('/admin/update_order_status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'role' not in session or session['role'] != 'admin':
        flash('Admin access required', 'danger')
        return redirect(url_for('home'))
    
    new_status = request.form['status']
    try:
        cur = mysql.connection.cursor()
        cur.execute(
            "UPDATE orders SET status = %s WHERE order_id = %s",
            (new_status, order_id)
        )
        mysql.connection.commit()
        cur.close()
        flash('Order status updated!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('admin_orders'))

# Run the application
if __name__ == '__main__':
    app.run(debug=True)