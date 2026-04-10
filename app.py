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

# Налаштування шляхів
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "app.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Налаштування завантаження зображень
UPLOAD_FOLDER = BASE_DIR / "static" / "images"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "svg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# Адмін-дані
ADMIN_PASSWORD = "dragon2026"
TELEGRAM_BOT_TOKEN = "8522017239:AAG2ckKbL3VAoeSZpdZqa-fB_26H3F413XQ"
TELEGRAM_CHAT_ID = "1682786328"

# --- МОДЕЛІ БАЗИ ДАНИХ ---

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=13)
    description = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), nullable=True)

class Order(db.Model):
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

# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_telegram_message(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=8)
    except:
        pass

def get_cart() -> list[dict]:
    cart = session.get("cart")
    return cart if isinstance(cart, list) else []

def save_cart(cart: list[dict]) -> None:
    session["cart"] = cart

# --- МАРШРУТИ МАГАЗИНУ ---

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
    if not p_id.isdigit(): return redirect(url_for("index"))
    product = Product.query.get_or_404(int(p_id))
    cart = get_cart()
    cart.append({
        "id": product.id, 
        "name": product.name, 
        "price": float(product.price), 
        "size": size, 
        "image": product.image_filename or "placeholder.svg"
    })
    save_cart(cart)
    return redirect(url_for("cart"))

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

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_items = get_cart()
    if not cart_items: return redirect(url_for("cart"))
    total = sum(item.get("price", 0) for item in cart_items)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        np = request.form.get("nova_poshta", "").strip()

        items_summary = "\n".join([f"- {i.get('name')} (Size: {i.get('size')})" for i in cart_items])
        new_order = Order(customer_name=name, customer_phone=phone, city=city, nova_poshta=np, items_summary=items_summary, total_price=total)
        
        db.session.add(new_order)
        db.session.commit()

        send_telegram_message(f"🔥 ЗАМОВЛЕННЯ 🔥\n👤 {name}\n📞 {phone}\n🏙 {city}\n📦 НП: {np}\n🛍 Товари:\n{items_summary}\n💰 {total} UAH")
        session.pop("cart", None)
        return redirect(url_for("success"))

    return render_template("checkout.html", total=total)

@app.route("/success")
def success():
    return render_template("success.html")

# --- АДМІН-МАРШРУТИ ---

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
    orders = Order.query.order_by(Order.created_at.desc()).all()
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin.html", orders=orders, leads=leads, products=products)

@app.route("/admin/product/add", methods=["POST"])
def admin_add_product():
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    
    name = request.form.get("name")
    category = request.form.get("category")
    price = float(request.form.get("price", 0))
    description = request.form.get("description")
    
    file = request.files.get("image")
    filename = None
    
    if file and allowed_file(file.filename):
        # Робимо унікальне ім'я файлу
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid4().hex}.{ext}"
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    
    new_product = Product(name=name, category=category, price=price, description=description, image_filename=filename)
    db.session.add(new_product)
    db.session.commit()
    return redirect(url_for("admin_panel"))

@app.route("/admin/product/delete/<int:product_id>")
def admin_delete_product(product_id):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    product = Product.query.get_or_404(product_id)
    # Можна також видалити сам файл з сервера, але для початку просто видалимо з бази
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for("admin_panel"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

@app.context_processor
def inject_cart_count():
    return {"cart_count": len(get_cart())}

# --- ЗАПУСК ---
if __name__ == "__main__":
    with app.app_context():
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        db.create_all()
    app.run(debug=True)