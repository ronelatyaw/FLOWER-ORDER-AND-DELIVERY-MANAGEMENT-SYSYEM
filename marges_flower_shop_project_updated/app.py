import hashlib
import os
import secrets
import smtplib
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import mysql.connector
from mysql.connector import Error
from decimal import Decimal
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "flower_shop_db",
}

def send_password_reset_email(email, reset_url):
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError("Password recovery is not configured. Set SMTP_HOST and SMTP_FROM.")

    message = EmailMessage()
    message["Subject"] = "Reset your Marge's Flower Shop password"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        f"Use this link to reset your password. It expires in one hour:\n\n{reset_url}\n\n"
        "If you did not request a password reset, you can ignore this email."
    )
    port = int(os.environ.get("SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.starttls()
        username = os.environ.get("SMTP_USERNAME")
        password = os.environ.get("SMTP_PASSWORD")
        if username:
            smtp.login(username, password or "")
        smtp.send_message(message)

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def fetch_all(query, params=()):
    conn = get_db()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def fetch_one(query, params=()):
    rows = fetch_all(query, params)
    return rows[0] if rows else None

def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/login", methods=["GET", "POST"])
def login():
    if "customer_id" in session:
        return redirect(url_for("user_home"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        account = fetch_one(
            """SELECT a.customer_id, a.password_hash, c.name
               FROM customer_accounts a
               JOIN customers c ON c.id=a.customer_id
               WHERE a.email=%s""",
            (email,),
        )
        if not account or not check_password_hash(account["password_hash"], password):
            flash("Email or password is incorrect.", "error")
            return render_template("admin_login.html", email=email, role="customer"), 401
        session.clear()
        session["customer_id"] = account["customer_id"]
        session["customer_name"] = account["name"]
        flash(f"Welcome back, {account['name']}!", "success")
        return redirect(url_for("user_home"))
    return render_template("admin_login.html", role="customer")

@app.route("/create-account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("Please complete all required fields.", "error")
            return render_template("create_account.html", name=name, email=email), 400
        if len(password) < 8:
            flash("Your password must be at least 8 characters long.", "error")
            return render_template("create_account.html", name=name, email=email), 400
        if password != confirm_password:
            flash("The passwords do not match.", "error")
            return render_template("create_account.html", name=name, email=email), 400

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM customers WHERE email=%s LIMIT 1", (email,))
            customer = cur.fetchone()
            if customer:
                customer_id = customer["id"]
            else:
                cur.execute(
                    "INSERT INTO customers (name, email) VALUES (%s, %s)",
                    (name, email),
                )
                customer_id = cur.lastrowid
            cur.execute(
                """INSERT INTO customer_accounts (customer_id, email, password_hash)
                   VALUES (%s, %s, %s)""",
                (customer_id, email, generate_password_hash(password)),
            )
            conn.commit()
            session.clear()
            session["customer_id"] = customer_id
            session["customer_name"] = name
            flash("Your account has been created.", "success")
            return redirect(url_for("user_home"))
        except Error:
            conn.rollback()
            app.logger.exception("Could not create customer account")
            flash("We couldn't create your account. That email may already be registered.", "error")
            return render_template("create_account.html", name=name, email=email), 400
        finally:
            cur.close()
            conn.close()
    return render_template("create_account.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        account = fetch_one("SELECT id FROM customer_accounts WHERE email=%s", (email,))
        if account:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute(
                    """DELETE FROM customer_password_resets
                       WHERE account_id=%s OR expires_at < NOW()""",
                    (account["id"],),
                )
                cur.execute(
                    """INSERT INTO customer_password_resets (account_id, token_hash, expires_at)
                       VALUES (%s, %s, DATE_ADD(NOW(), INTERVAL 1 HOUR))""",
                    (account["id"], token_hash),
                )
                conn.commit()
            except Error:
                conn.rollback()
                app.logger.exception("Could not create password reset request")
                flash("We couldn't start password recovery. Please try again.", "error")
                return render_template("forgot_password.html", email=email), 500
            finally:
                cur.close()
                conn.close()
            try:
                send_password_reset_email(
                    email,
                    url_for("reset_password", token=token, _external=True),
                )
            except (OSError, RuntimeError, smtplib.SMTPException, ValueError):
                app.logger.exception("Could not send password reset email")
                conn = get_db()
                try:
                    cur = conn.cursor()
                    cur.execute(
                        "DELETE FROM customer_password_resets WHERE token_hash=%s",
                        (token_hash,),
                    )
                    conn.commit()
                finally:
                    cur.close()
                    conn.close()
                flash("We couldn't send a reset email. Please try again later or contact the shop.", "error")
                return render_template("forgot_password.html", email=email), 503
        flash("If an account exists for that email, password reset instructions have been sent.", "success")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    reset_request = fetch_one(
        """SELECT id, account_id FROM customer_password_resets
           WHERE token_hash=%s AND expires_at > NOW()""",
        (token_hash,),
    )
    if not reset_request:
        flash("That password reset link is invalid or expired. Please request another one.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Your password must be at least 8 characters long.", "error")
            return render_template("reset_password.html", token=token), 400
        if password != confirm_password:
            flash("The passwords do not match.", "error")
            return render_template("reset_password.html", token=token), 400
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE customer_accounts SET password_hash=%s WHERE id=%s",
                (generate_password_hash(password), reset_request["account_id"]),
            )
            cur.execute(
                "DELETE FROM customer_password_resets WHERE account_id=%s",
                (reset_request["account_id"],),
            )
            conn.commit()
        except Error:
            conn.rollback()
            app.logger.exception("Could not reset customer password")
            flash("We couldn't update your password. Please try again.", "error")
            return render_template("reset_password.html", token=token), 500
        finally:
            cur.close()
            conn.close()
        flash("Your password has been reset. Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", token=token)

@app.route("/user", methods=["GET", "POST"])
def user_home():
    """Public customer page: browse flowers, place orders, and track by email."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        address = request.form.get("address", "").strip()
        product_id = request.form.get("product_id")
        try:
            quantity = max(1, int(request.form.get("quantity", 1)))
            if not all([name, email, address, product_id]):
                flash("Please complete your name, email, delivery address, and product.", "error")
                return redirect(url_for("user_home"))
            product = fetch_one("SELECT id, price, stock FROM products WHERE id=%s", (product_id,))
            if not product:
                flash("Please choose a valid product.", "error")
                return redirect(url_for("user_home"))
            if product["stock"] < quantity:
                flash("There is not enough stock for that quantity.", "error")
                return redirect(url_for("user_home"))
            existing = fetch_one("SELECT id FROM customers WHERE email=%s", (email,))
            conn = get_db()
            try:
                cur = conn.cursor()
                if existing:
                    customer_id = existing["id"]
                    cur.execute("UPDATE customers SET name=%s, phone=%s, address=%s WHERE id=%s", (name, phone, address, customer_id))
                else:
                    cur.execute("INSERT INTO customers (name, phone, email, address) VALUES (%s,%s,%s,%s)", (name, phone, email, address))
                    customer_id = cur.lastrowid
                total = Decimal(str(product["price"])) * quantity
                cur.execute("INSERT INTO orders (customer_id, product_id, quantity, total, status) VALUES (%s,%s,%s,%s,'Pending')", (customer_id, product_id, quantity, total))
                order_id = cur.lastrowid
                cur.execute("UPDATE orders SET order_code=%s WHERE id=%s", (f"FOD-{order_id:04d}", order_id))
                cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (quantity, product_id))
                conn.commit()
                flash(f"Order FOD-{order_id:04d} placed successfully! You can track it with your email address.", "success")
            except Error:
                conn.rollback()
                raise
            finally:
                cur.close()
                conn.close()
            return redirect(url_for("user_home", email=email))
        except (Error, ValueError) as e:
            flash(f"Unable to place order: {e}", "error")
            return redirect(url_for("user_home"))
    products = fetch_all("SELECT * FROM products WHERE stock > 0 ORDER BY name")
    email = request.args.get("email", "").strip().lower()
    user_orders = []
    if email:
        user_orders = fetch_all("""SELECT o.order_code, o.quantity, o.total, o.status, o.order_date, p.name AS product, p.image
                                   FROM orders o JOIN customers c ON c.id=o.customer_id
                                   JOIN products p ON p.id=o.product_id
                                   WHERE c.email=%s ORDER BY o.order_date DESC, o.id DESC""", (email,))
    return render_template("user.html", products=products, user_orders=user_orders, search_email=email)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    if "customer_id" in session and "admin_id" not in session:
        return redirect(url_for("user_home"))
    if "admin_id" not in session:
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            account = fetch_one(
                "SELECT id, email, password_hash FROM admin_accounts WHERE email=%s",
                (email,),
            )
            if not account or not check_password_hash(account["password_hash"], password):
                flash("Email or password is incorrect.", "error")
                return render_template("admin_login.html", email=email, role="admin"), 401
            session.clear()
            session["admin_id"] = account["id"]
            session["admin_email"] = account["email"]
            flash("Welcome to the admin dashboard.", "success")
            return redirect(url_for("dashboard"))
        role = request.args.get("role", "customer")
        if role not in {"admin", "customer"}:
            role = "customer"
        return render_template("admin_login.html", role=role)

    try:
        stats = {
            "total_orders": fetch_one("SELECT COUNT(*) AS n FROM orders")["n"],
            "pending_orders": fetch_one("SELECT COUNT(*) AS n FROM orders WHERE status='Pending'")["n"],
            "delivered_orders": fetch_one("SELECT COUNT(*) AS n FROM orders WHERE status='Delivered'")["n"],
            "total_customers": fetch_one("SELECT COUNT(*) AS n FROM customers")["n"],
            "total_products": fetch_one("SELECT COUNT(*) AS n FROM products")["n"],
            "total_sales": fetch_one("SELECT COALESCE(SUM(total),0) AS n FROM orders WHERE status='Delivered'")["n"],
        }
        status_rows = fetch_all("SELECT status, COUNT(*) AS count FROM orders GROUP BY status")
        sales_rows = fetch_all("""
            SELECT DATE_FORMAT(order_date, '%b') AS month,
                   MONTH(order_date) AS month_no,
                   COALESCE(SUM(total),0) AS total
            FROM orders
            WHERE YEAR(order_date)=YEAR(CURDATE())
            GROUP BY MONTH(order_date), DATE_FORMAT(order_date, '%b')
            ORDER BY month_no
        """)
        recent_orders = fetch_all("""
            SELECT o.id, o.order_code, c.name AS customer, p.name AS product,
                   o.quantity, o.total, o.status, o.order_date
            FROM orders o
            JOIN customers c ON c.id=o.customer_id
            JOIN products p ON p.id=o.product_id
            ORDER BY o.order_date DESC, o.id DESC LIMIT 7
        """)
        top_products = fetch_all("""
            SELECT p.name, COALESCE(SUM(o.quantity),0) AS orders_count
            FROM products p LEFT JOIN orders o ON o.product_id=p.id
            GROUP BY p.id, p.name ORDER BY orders_count DESC LIMIT 5
        """)
        low_stock = fetch_all("SELECT name, price, stock FROM products WHERE stock <= 5 ORDER BY stock ASC LIMIT 5")
        return render_template("dashboard.html", stats=stats, status_rows=status_rows,
                               sales_rows=sales_rows, recent_orders=recent_orders,
                               top_products=top_products, low_stock=low_stock, active="dashboard")
    except Error as e:
        return render_template("setup_error.html", error=str(e)), 500

@app.route("/products", methods=["GET", "POST"])
@admin_required
def products():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "Bouquet").strip()
        price = request.form.get("price", "0")
        stock = request.form.get("stock", "0")
        image = request.form.get("image", "🌷").strip() or "🌷"
        if not name:
            flash("Please enter a product name.", "error")
        else:
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO products (name, category, price, stock, image) VALUES (%s,%s,%s,%s,%s)",
                            (name, category, price, stock, image))
                conn.commit()
                flash("Product added successfully.", "success")
            except Error as e:
                flash(f"Could not add product: {e}", "error")
            finally:
                cur.close()
                conn.close()
        return redirect(url_for("products"))
    items = fetch_all("SELECT * FROM products ORDER BY id DESC")
    return render_template("products.html", products=items, active="products")

@app.route("/products/delete/<int:product_id>", methods=["POST"])
@admin_required
def delete_product(product_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=%s", (product_id,))
        conn.commit()
        flash("Product deleted.", "success")
    except Error as e:
        flash(f"Cannot delete product: {e}", "error")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for("products"))

@app.route("/orders", methods=["GET", "POST"])
@admin_required
def orders():
    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        product_id = request.form.get("product_id")
        quantity = max(1, int(request.form.get("quantity", 1)))
        try:
            product = fetch_one("SELECT price, stock FROM products WHERE id=%s", (product_id,))
            if not product:
                flash("Choose a valid product.", "error")
            elif product["stock"] < quantity:
                flash("Not enough stock for that quantity.", "error")
            else:
                total = Decimal(str(product["price"])) * quantity
                conn = get_db()
                try:
                    cur = conn.cursor()
                    cur.execute("""INSERT INTO orders (customer_id, product_id, quantity, total, status)
                                   VALUES (%s,%s,%s,%s,'Pending')""",
                                (customer_id, product_id, quantity, total))
                    order_id = cur.lastrowid
                    cur.execute("UPDATE orders SET order_code=%s WHERE id=%s", (f"FOD-{order_id:04d}", order_id))
                    cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s", (quantity, product_id))
                    conn.commit()
                    flash("Order created successfully.", "success")
                finally:
                    cur.close()
                    conn.close()
        except (Error, ValueError) as e:
            flash(f"Could not create order: {e}", "error")
        return redirect(url_for("orders"))
    all_orders = fetch_all("""SELECT o.*, c.name AS customer, p.name AS product
                              FROM orders o JOIN customers c ON c.id=o.customer_id
                              JOIN products p ON p.id=o.product_id
                              ORDER BY o.order_date DESC, o.id DESC""")
    customers = fetch_all("SELECT id, name FROM customers ORDER BY name")
    products_list = fetch_all("SELECT id, name, price, stock FROM products WHERE stock > 0 ORDER BY name")
    return render_template("orders.html", orders=all_orders, customers=customers,
                           products=products_list, active="orders")

@app.route("/orders/status/<int:order_id>", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("status")
    allowed = {"Pending", "Processing", "On Delivery", "Delivered", "Cancelled"}
    if status not in allowed:
        flash("Invalid order status.", "error")
    else:
        conn = get_db()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
            conn.commit()
            flash("Order status updated.", "success")
        except Error as e:
            flash(f"Could not update status: {e}", "error")
        finally:
            cur.close()
            conn.close()
    return redirect(request.referrer or url_for("orders"))

@app.route("/customers", methods=["GET", "POST"])
@admin_required
def customers():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        if not name:
            flash("Customer name is required.", "error")
        else:
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute("INSERT INTO customers (name, phone, email, address) VALUES (%s,%s,%s,%s)",
                            (name, phone, email, address))
                conn.commit()
                flash("Customer added.", "success")
            except Error as e:
                flash(f"Could not add customer: {e}", "error")
            finally:
                cur.close()
                conn.close()
        return redirect(url_for("customers"))
    people = fetch_all("SELECT * FROM customers ORDER BY id DESC")
    return render_template("customers.html", customers=people, active="customers")

@app.route("/settings")
@admin_required
def settings():
    return render_template("settings.html", active="settings")

@app.route("/api/sales")
@admin_required
def api_sales():
    rows = fetch_all("""SELECT DATE_FORMAT(order_date, '%b') AS month, SUM(total) AS total
                        FROM orders WHERE status='Delivered' AND YEAR(order_date)=YEAR(CURDATE())
                        GROUP BY MONTH(order_date), DATE_FORMAT(order_date, '%b')
                        ORDER BY MONTH(order_date)""")
    return jsonify([{"month": r["month"], "total": float(r["total"] or 0)} for r in rows])

@app.route("/logout")
def logout():
    if "customer_id" in session:
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))
    flash("You have been logged out (demo interface).", "success")
    return redirect(url_for("dashboard"))

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
