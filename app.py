import os
import re
import requests
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "dragon_secret_shield_2026_key"

# Налаштування бази (V2 для стабільності)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dragon_v2.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Налаштування фото
UPLOAD_FOLDER = BASE_DIR / "static" / "images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# Дані
ADMIN_PASSWORD = "dragon2026"
TELEGRAM_BOT_TOKEN = "8522017239:AAG2ckKbL3VAoeSZpdZqa-fB_26H3F413XQ"
TELEGRAM_CHAT_ID = "1682786328"

# --- МОДЕЛІ ---

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=13)
    description = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), nullable=True)

class Order(db.Model):
    __tablename__ = 'orders_v2'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    nova_poshta = db.Column(db.String(255), nullable=False)
    items_summary = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Новий")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# --- АВТО-ЗАПОВНЕННЯ КОЛЕКЦІЇ ---
def seed_products():
    if Product.query.count() == 0:
        items = [
            Product(name="Imperial Gold Dragon", category="Shirt", price=3300.0, description="A digital masterpiece born from 40,000 stitches of gold-threaded contouring. High-grade silk meets liquid gold logic.", image_filename=None),
            Product(name="Void Wave Trousers", category="Trousers", price=3000.0, description="Structural minimalism designed by algorithms. Premium black wool-blend with gold embroidery.", image_filename=None),
            Product(name="Minimalist Gold Thread", category="Shirt", price=2500.0, description="Elegant simplicity meets high-tech luxury. Subtle gold line work.", image_filename=None),
        ]
        db.session.add_all(items)
        db.session.commit()

# --- ФУНКЦІЇ ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=8)
    except: pass

def get_cart():
    return session.get("cart", [])

# --- МАРШРУТИ ---

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
    size = request.form.get("size", "Standard")
    product = Product.query.get_or_404(int(p_id))
    cart = get_cart()
    cart.append({"id": product.id, "name": product.name, "price": float(product.price), "size": size, "image": product.image_filename or "placeholder.svg"})
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/cart")
def cart():
    cart_items = get_cart()
    total = sum(item.get("price", 0) for item in cart_items)
    return render_template("cart.html", cart_items=cart_items, total=total)

@app.post("/remove_from_cart/<int:index>")
def remove_from_cart(index):
    cart = get_cart()
    if 0 <= index < len(cart):
        cart.pop(index)
        session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_items = get_cart()
    if not cart_items: return redirect(url_for("cart"))
    total = sum(item.get("price", 0) for item in cart_items)
    if request.method == "POST":
        try:
            name, phone = request.form.get("name"), request.form.get("phone")
            city, np = request.form.get("city"), request.form.get("nova_poshta")
            summary = "\n".join([f"- {i.get('name')} ({i.get('size')})" for i in cart_items])
            order = Order(customer_name=name, customer_phone=phone, city=city, nova_poshta=np, items_summary=summary, total_price=total)
            db.session.add(order); db.session.commit()
            send_telegram_message(f"🔥 ЗАМОВЛЕННЯ 🔥\n👤 {name}\n📞 {phone}\n🏙 {city}\n📦 НП: {np}\n🛍 Товари:\n{summary}\n💰 {total} UAH")
            session.pop("cart", None)
            return redirect(url_for("success"))
        except Exception as e:
            return f"<div style='background:#000; color:#ff4444; padding:50px;'><h2>ERROR:</h2><p>{str(e)}</p></div>"
    return render_template("checkout.html", total=total)

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if email:
        if not Lead.query.filter_by(email=email).first():
            db.session.add(Lead(email=email)); db.session.commit()
            send_telegram_message(f"👤 New Waitlist Member: {email}")
        return redirect(url_for("success"))
    return redirect(url_for("index"))

@app.route("/success")
def success(): return render_template("success.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
    return render_template("admin_login.html")

@app.route("/admin")
def admin_panel():
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    return render_template("admin.html", orders=Order.query.all(), leads=Lead.query.all(), products=Product.query.all())

@app.route("/admin/product/add", methods=["POST"])
def admin_add_product():
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    name, price = request.form.get("name"), float(request.form.get("price", 0))
    desc, cat = request.form.get("description"), request.form.get("category")
    file = request.files.get("image")
    filename = f"{uuid4().hex}.{file.filename.rsplit('.', 1)[1].lower()}" if file and allowed_file(file.filename) else None
    if filename: file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    db.session.add(Product(name=name, price=price, description=desc, category=cat, image_filename=filename))
    db.session.commit(); return redirect(url_for("admin_panel"))

@app.route("/admin/product/delete/<int:product_id>")
def admin_delete_product(product_id):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    db.session.delete(Product.query.get_or_404(product_id))
    db.session.commit(); return redirect(url_for("admin_panel"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None); return redirect(url_for("admin_login"))

@app.context_processor
def inject_cart_count():
    cart = session.get("cart", [])
    return {"cart_count": len(cart)}

# --- СТАРТ ---
with app.app_context():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    db.create_all()
    seed_products() # ОЦЕ ПОВЕРНЕ ТВОЮ КОЛЕКЦІЮ

if __name__ == "__main__":
    app.run(debug=True)