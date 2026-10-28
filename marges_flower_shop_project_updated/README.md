# Marge's Flower Shop — Flower Order & Delivery Management System

A beginner-friendly Flask website inspired by the provided dashboard screenshot. It uses HTML templates, CSS, JavaScript, Bootstrap 5, Flask, and MySQL from XAMPP.

## Included pages
- Customer storefront at `/user`: a separate customer-facing page to browse bouquets, place orders, and track orders by email
- Customer authentication at `/login` and `/create-account`, with password recovery at `/forgot-password`
- Admin login at `/` with protected dashboard and shop management pages
- Dashboard with order/customer/product/sales cards, order status chart, sales chart, top products, recent orders, and low-stock products
- Products: list, add, and delete products
- Orders: create orders and update order status
- Customers: add and view customers
- Settings page (starter page)
- `schema.sql` with tables and demo data

## Requirements
- Python 3.10 or newer
- XAMPP with MySQL running
- Visual Studio Code (or another editor)

## Setup
1. Start **MySQL** in XAMPP. Apache is not required for this Flask app.
2. Open phpMyAdmin at `http://localhost/phpmyadmin`.
3. Choose **Import**, select `schema.sql`, then click **Import/Go**. This creates `flower_shop_db`.
4. Open this project folder in Visual Studio Code.
5. Open the VS Code terminal in the project folder.
6. Create and activate a virtual environment (optional but recommended):
   - Windows: `python -m venv .venv`
   - PowerShell: `.\.venv\Scripts\Activate.ps1`
7. Install packages: `pip install -r requirements.txt`
8. Run the app: `python app.py`
9. Open `http://127.0.0.1:5000` in your browser.

## Default admin login
Import or re-import `schema.sql` to create the admin account in MySQL. The default login is:
- Email: `admin@margesflowershop.com`
- Password: `MargeAdmin2026!`

This default account is for local development. Change the password before deploying the app publicly.

## Customer accounts and password recovery
Customer accounts use hashed passwords. If the database already exists, import the updated `schema.sql` again in phpMyAdmin to create the account and password-reset tables; the existing demo inserts are safe to rerun.

Password reset links are emailed using SMTP. Configure these environment variables before using password recovery:
- `SMTP_HOST` and `SMTP_FROM` (required)
- `SMTP_PORT` (optional, defaults to `587`)
- `SMTP_USERNAME` and `SMTP_PASSWORD` (optional, for authenticated SMTP)

For deployment, also set `FLASK_SECRET_KEY` to a long, random secret and keep it private. The app generates a temporary key automatically for local development when this variable is not set.

## Database configuration
The default settings in `app.py` use XAMPP's common local MySQL settings:
- host: `localhost`
- user: `root`
- password: empty
- database: `flower_shop_db`

If your MySQL root account has a password, update `DB_CONFIG` in `app.py`.

## Important notes
- This is a local admin dashboard starter project, not a production-ready online store.
- The admin dashboard is still a demo interface; customer accounts apply to the separate storefront and do not protect admin pages.
- Customers can still place orders and track them without logging in.
- For real deployment, add authentication, CSRF protection, input validation, and environment-based secrets.
- The product image column currently uses emoji so it works without uploading image files.
