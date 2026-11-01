# Hosting the eshop on PythonAnywhere

The shop keeps its data in `instance/` (SQLite database, uploaded images, secret key), so it needs a host
with a persistent disk. PythonAnywhere's free plan works for a demo.

1. **Account.** Sign up at pythonanywhere.com. Your site will be `YOUR_USERNAME.pythonanywhere.com`.
2. **Code.** Open a Bash console and run:
   ```
   git clone https://github.com/Christos2424/eshop-project.git
   cd eshop-project/flask_eshop
   python3.13 -m venv ~/venv && source ~/venv/bin/activate   # use a Python version listed under Web > Python version
   pip install -r requirements.txt
   ```
3. **Settings.** Create `flask_eshop/.env` (copy `.env.example`) with:
   ```
   SECRET_KEY=<a long random string>
   ADMIN_EMAIL=you@example.com
   ADMIN_PASSWORD=<a strong password>
   SESSION_COOKIE_SECURE=1
   ```
4. **Database.** In the same console, still in `flask_eshop` with the venv active:
   ```
   flask --app run init-db
   flask --app run seed-products
   ```
   The tables are created and the admin account gets your `ADMIN_PASSWORD`. If `admin` already exists,
   change its password with `flask --app run set-password you@example.com`.
5. **Web app.** Web tab > *Add a new web app* > *Manual configuration* > pick the same Python version.
   - Virtualenv: `/home/YOUR_USERNAME/venv`
   - WSGI configuration file: replace its contents with `deploy/pythonanywhere_wsgi.py` and fix `PROJECT`.
   - Static files: URL `/static/` -> directory `/home/YOUR_USERNAME/eshop-project/flask_eshop/eshop/static`
6. **Reload** the web app and open your address. HTTPS is on by default.

**Updating:** `git pull` in the console, `pip install -r requirements.txt`, then press *Reload*.

**Backups:** download `instance/` now and then (Files tab); it holds all users, orders and images.

**Note:** the free plan blocks downloading product images from outside URLs (only whitelisted sites are
reachable). Uploading image files from your computer works.

## On a VPS instead

Run `gunicorn -w 3 -b 127.0.0.1:8000 "eshop:create_app()"` as a systemd service from `flask_eshop`
(with the same `.env`) and put Nginx or Caddy in front for HTTPS.

powershell -ExecutionPolicy Bypass -File deploy\start_public.ps1
