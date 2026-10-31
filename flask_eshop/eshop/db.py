import os
import secrets
import sqlite3
from contextlib import contextmanager

import click
from flask import current_app, g

from .security import hash_password


def get_db():
    """Get database connection"""
    if '_database' not in g:
        g._database = sqlite3.connect(current_app.config['DATABASE'])
        g._database.row_factory = sqlite3.Row
    return g._database


def close_db(exception=None):
    """Close database connection at the end of request"""
    db = g.pop('_database', None)
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


def get_categories():
    with get_cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND category != '' ORDER BY category")
        return [row[0] for row in cur.fetchall()]


def init_db(database):
    """Initialize the database with required tables and sample data"""
    conn = sqlite3.connect(database)
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
    cursor.execute("SELECT 1 FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@eshop.com')
        admin_password = os.environ.get('ADMIN_PASSWORD') or secrets.token_urlsafe(12)
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_email, hash_password(admin_password), 'admin'))
        if not os.environ.get('ADMIN_PASSWORD'):
            click.echo(f"Created admin account {admin_email} with password: {admin_password}")

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


@click.command('init-db')
def init_db_command():
    """Create tables, the admin user and sample products if missing."""
    init_db(current_app.config['DATABASE'])
    click.echo('Database initialized successfully!')


@click.command('set-password')
@click.argument('email')
@click.password_option()
def set_password_command(email, password):
    """Change the password of the user with this email."""
    with get_cursor() as cur:
        cur.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hash_password(password), email))
        updated = cur.rowcount
    if updated:
        click.echo(f"Password updated for {email}")
    else:
        raise click.ClickException(f"No user with email {email}")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(set_password_command)
    # Always ensure tables exist
    init_db(app.config['DATABASE'])
