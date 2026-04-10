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
    "trousers": ["S", "M", "L", "XL"],
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
                name="Imperial Gold Dragon",
                category="Shirt",
                price=3300.0,
                stock=13,
                description="A digital masterpiece born from 40,000 stitches of gold-threaded contouring. High-grade silk meets liquid gold logic. Strictly Made-to-Order.",
                image_filename=None
            ),
            Product(
                name="Void Wave Trousers",
                category="Trousers",
                price=3000.0,
                stock=13,
                description="Structural minimalism designed by algorithms. Premium black wool-blend with delicate gold wave embroidery, symbolizing the fluidity of power.",
                image_filename=None
            ),
            Product(
                name="Minimalist Gold Thread",
                category="Shirt",
                price=2500.0,
                stock=13,
                description="Elegant simplicity meets high-tech luxury. Subtle gold line work creates understated sophistication for the discerning digital collector.",
                image_filename=None
            ),
        ]
        db.session.add_all(demo_items)
        db.session.commit()

def is_valid_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

def normalize_category(category: str) -> str | None:
    category_value = (category or "").strip().lower()
    if category_value in {"shirt", "shirts", "сорочка", "сорочки"}: return "shirt"
    if category_value in {"trousers", "pants", "штани"}: return "trousers"
    return None

def get_cart() -> list[dict]:
    cart = session.get("cart")
    return cart if isinstance(cart, list) else []

def save_cart(cart: list[dict]) -> None:
    session["cart"] = cart

def send_telegram_message(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=8)
    except: pass

@app.route("/")
def index():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("index.html", products=products)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", product=product)

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    p_id = request.form.get("product_id", "")
    size = request.form.get("size", "")
    if not p_id.isdigit(): return redirect(url_for("index"))
    product = Product.query.get_or_404(int(p_id))
    cart = get_cart()
    cart.append({
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "size": size,
        "image": product.image_filename or "placeholder.svg",
    })
    save_cart(cart)
    send_telegram_message(f"🔥 Added: {product.name} ({size})")
    return redirect(url_for("success"))

@app.route("/cart")
def cart():
    cart_items = get_cart()
    total = sum(item.get("price", 0) for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.post("/remove_from_cart/<int:index>")
def remove_from_cart(index: int):
    cart = get_cart()
    if 0 <= index < len(cart):
        cart.pop(index)
        save_cart(cart)
    return redirect(url_for("cart"))

@app.post("/cart/checkout")
def checkout_demo():
    flash("Demo Mode: Checkout disabled.", "info")
    return redirect(url_for("cart"))

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if email and is_valid_email(email):
        if not Lead.query.filter_by(email=email).first():
            db.session.add(Lead(email=email))
            db.session.commit()
            send_telegram_message(f"👤 New Member: {email}")
            return redirect(url_for("success"))
    return redirect(url_for("index"))

@app.route("/success")
def success():
    return render_template("success.html")

@app.context_processor
def inject_cart_count():
    return {"cart_count": len(get_cart())}

def initialize():
    IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    db.create_all()
    seed_products()

with app.app_context():
    initialize()

if __name__ == "__main__":
    app.run(debug=True)