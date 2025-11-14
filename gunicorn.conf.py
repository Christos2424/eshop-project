import multiprocessing

# Bind to a specific address and port
bind = "0.0.0.0:8000"  # Accessible only from the local machine
# OR use the following to accept connections from outside
# bind = "0.0.0.0:8000"

# Number of worker processes. A common formula is (2 x $cores) + 1
workers = multiprocessing.cpu_count() * 2 + 1

# Use the 'gthread' worker class for potentially better performance with threads
worker_class = "gthread"

# Number of threads per worker
threads = 4

# Directory where your Flask application is located
chdir = "/path/to/your/app"

# Module and callable for your WSGI application
wsgi_app = "app:app"  # For a Flask app in app.py

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"

# Do not use auto-reload in production
reload = False