import csv
import re
import requests
from io import StringIO
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = "dragon_secret_shield_2026_key"
app.config["SECRET_KEY"] = app.secret_key
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

ADMIN_PASSWORD = "dragon2026"
IMAGE_UPLOAD_DIR = Path(app.static_folder) / "images"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}
SIZE_GUIDE = {
    "shirt": ["S", "M", "L", "XL"],
    "trousers": ["30", "32", "34", "36"],
}
TELEGRAM_BOT_TOKEN = "8522017239:AAG2ckKbL3VAoeSZpdZqa-fB_26H3F413XQ".strip("[] ")
TELEGRAM_CHAT_ID = "1682786328".strip("[] ")


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), nullable=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Новий")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    product = db.relationship("Product", backref=db.backref("orders", lazy=True))


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def seed_products() -> None:
    if Product.query.count() == 0:
        demo_items = [
            Product(
                name="Сорочка з драконом",
                category="Сорочки",
                price=1299.0,
                stock=10,
                description="Преміальна сорочка з вишивкою дракона для виразного образу.",
            ),
            Product(
                name="Худі Shadow Flame",
                category="Худі",
                price=1999.0,
                stock=7,
                description="Тепле худі у темній естетиці з акцентом на комфорт та стиль.",
            ),
            Product(
                name="Футболка Black Scale",
                category="Футболки",
                price=899.0,
                stock=15,
                description="Базова футболка з характерним дизайном для щоденного носіння.",
            ),
        ]
        db.session.add_all(demo_items)
        db.session.commit()


def is_allowed_image(filename: str) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def normalize_category(category: str) -> str | None:
    category_value = (category or "").strip().lower()
    if category_value in {"shirt", "shirts", "сорочка", "сорочки"}:
        return "shirt"
    if category_value in {"trousers", "pants", "штани"}:
        return "trousers"
    return None


def get_cart() -> list[dict]:
    cart = session.get("cart")
    if isinstance(cart, list):
        return cart
    return []


def save_cart(cart: list[dict]) -> None:
    session["cart"] = cart


def send_telegram_message(message: str) -> None:
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(
            telegram_url,
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=8,
        )
        response.raise_for_status()
    except Exception:
        # Telegram alerts are optional and must not break the site flow.
        pass


def initialize_app_data() -> None:
    IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.create_all()
    seed_products()


with app.app_context():
    initialize_app_data()


def is_admin_authenticated() -> bool:
    return bool(session.get("admin_logged_in"))


@app.before_request
def protect_admin_routes() -> None:
    admin_login_path = url_for("admin_login")
    admin_logout_path = url_for("admin_logout")
    if (
        request.path.startswith("/admin")
        and request.path not in {admin_login_path, admin_logout_path}
    ):
        if not is_admin_authenticated():
            return redirect(admin_login_path)


@app.after_request
def disable_admin_cache(response):
    if request.path.startswith("/admin"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("index.html", products=products, size_guide=SIZE_GUIDE)


@app.route("/success")
def success():
    return render_template("success.html")
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    # Шукаємо товар у базі. Якщо хтось введе неіснуючий ID, сайт видасть помилку 404, а не зламається.
    product = Product.query.get_or_404(product_id)
    # Відкриваємо новий шаблон і передаємо туди дані цього товару та розмірну сітку
    return render_template("product_detail.html", product=product, size_guide=SIZE_GUIDE)

@app.post("/order/<int:product_id>")
def create_test_order(product_id: int):
    product = Product.query.get_or_404(product_id)
    if product.stock <= 0:
        flash("This product is currently out of stock.", "danger")
        return redirect(url_for("index"))

    order = Order(
        customer_name="Тестовий покупець",
        customer_email="test@example.com",
        product_id=product.id,
    )
    product.stock -= 1
    db.session.add(order)
    db.session.commit()
    flash("Test order created successfully.", "success")
    return redirect(url_for("index"))


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    product_id = request.form.get("product_id", "").strip()
    size = request.form.get("size", "").strip()
    if not product_id.isdigit():
        flash("Invalid product selected.", "danger")
        return redirect(url_for("index") + "#collection")

    product = Product.query.get_or_404(int(product_id))
    category_key = normalize_category(product.category)
    if not category_key:
        flash("This product category has no size guide configured.", "danger")
        return redirect(url_for("index") + "#collection")

    allowed_sizes = SIZE_GUIDE.get(category_key, [])
    if size not in allowed_sizes:
        flash("Please choose a valid size.", "danger")
        return redirect(url_for("index") + "#collection")

    cart = get_cart()
    cart.append(
        {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "size": size,
            "image": product.image_filename or "placeholder.svg",
        }
    )
    save_cart(cart)
    send_telegram_message(f"New potential order! Product: {product.name}, Size: {size}")
    flash(f"{product.name} was added to your cart.", "success")
    return redirect(url_for("success"))


@app.get("/cart")
def cart():
    cart_items = get_cart()
    total = sum(float(item.get("price", 0)) for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)


@app.post("/remove_from_cart/<int:index>")
def remove_from_cart(index: int):
    cart = get_cart()
    if 0 <= index < len(cart):
        cart.pop(index)
        save_cart(cart)
        flash("Item removed from cart.", "info")
    else:
        flash("Item was not found in your cart.", "danger")
    return redirect(url_for("cart"))


@app.post("/cart/checkout")
def checkout_demo():
    flash("Thank you for testing! Checkout is disabled in demo mode.", "info")
    return redirect(url_for("cart"))


@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if not email or not is_valid_email(email):
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for("index") + "#contact")

    existing_lead = Lead.query.filter_by(email=email).first()
    if existing_lead:
        flash("This email is already on the waitlist.", "info")
        return redirect(url_for("index") + "#contact")

    lead = Lead(email=email)
    db.session.add(lead)
    db.session.commit()
    send_telegram_message(f"New Waitlist Subscriber: {email}")
    flash("Thank you! You've been added to the waitlist.", "success")
    return redirect(url_for("success"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if is_admin_authenticated():
        return redirect(url_for("admin_panel"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        flash("Invalid password.", "danger")
    return render_template("admin_login.html")


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_panel():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    products = Product.query.order_by(Product.id.desc()).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template("admin.html", products=products, orders=orders, leads=leads)


@app.post("/admin/products/add")
def add_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    stock = request.form.get("stock", "").strip()
    image = request.files.get("image")

    if not all([name, category, description, price, stock]):
        flash("All product fields are required.", "danger")
        return redirect(url_for("admin_panel"))

    try:
        price_value = float(price)
        stock_value = int(stock)
        if price_value < 0 or stock_value < 0:
            raise ValueError
    except ValueError:
        flash("Price or quantity has an invalid value.", "danger")
        return redirect(url_for("admin_panel"))

    image_filename = None
    if image and image.filename:
        raw_name = secure_filename(image.filename)
        if not is_allowed_image(raw_name):
            flash("Allowed formats: png, jpg, jpeg, webp, gif, svg.", "danger")
            return redirect(url_for("admin_panel"))
        extension = raw_name.rsplit(".", 1)[1].lower()
        image_filename = f"{uuid4().hex}.{extension}"
        image.save(IMAGE_UPLOAD_DIR / image_filename)

    new_product = Product(
        name=name,
        category=category,
        description=description,
        price=price_value,
        stock=stock_value,
        image_filename=image_filename,
    )
    db.session.add(new_product)
    db.session.commit()
    flash("Product added successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.post("/admin/products/<int:product_id>/delete")
def delete_product(product_id: int):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    product = Product.query.get_or_404(product_id)
    if product.image_filename:
        image_path = IMAGE_UPLOAD_DIR / product.image_filename
        if image_path.exists():
            image_path.unlink()

    Order.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.post("/admin/orders/<int:order_id>/ship")
def mark_order_shipped(order_id: int):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    order = Order.query.get_or_404(order_id)
    if order.status == "Новий":
        order.status = "Відправлено"
        db.session.commit()
        flash("Order marked as shipped.", "success")
    else:
        flash("This order has already been processed.", "info")
    return redirect(url_for("admin_panel"))


@app.get("/admin/leads/export")
def export_leads_csv():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["id", "email", "created_at"])
    for lead in leads:
        writer.writerow([lead.id, lead.email, lead.created_at.isoformat()])

    response = app.response_class(
        csv_buffer.getvalue(),
        mimetype="text/csv",
    )
    response.headers["Content-Disposition"] = (
        f"attachment; filename=waitlist_leads_{datetime.utcnow():%Y%m%d_%H%M%S}.csv"
    )
    return response


@app.context_processor
def inject_cart_count():
    return {"cart_count": len(get_cart())}


if __name__ == "__main__":
    app.run(debug=True)
