import os
import re
import requests
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

load_dotenv(Path(__file__).resolve().parent / '.env')
SENT_MESSAGES = {}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-dev-key-change-me")

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
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
NOVA_POSHTA_API_KEY = os.environ.get("NOVA_POSHTA_API_KEY", "")

# --- МОДЕЛІ ---

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=13)
    description = db.Column(db.Text, nullable=False, default="")
    image_filename = db.Column(db.String(255), nullable=True)
    gallery_images = db.Column(db.Text, nullable=True)

    @property
    def all_images(self):
        """Return list of all images: main + gallery extras."""
        imgs = []
        if self.image_filename:
            imgs.append(self.image_filename)
        if self.gallery_images:
            imgs.extend([f.strip() for f in self.gallery_images.split(",") if f.strip()])
        return imgs if imgs else ["placeholder.svg"]

class Order(db.Model):
    __tablename__ = 'orders_v2'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    nova_poshta = db.Column(db.String(255), nullable=False)
    items_summary = db.Column(db.Text, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default="NEW")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

# --- АВТО-ЗАПОВНЕННЯ КОЛЕКЦІЇ ---
def seed_products():
    if Product.query.count() == 0:
        items = [
            Product(name="Imperial Gold Dragon", category="Shirt", price=3300.0,
                    description="A digital masterpiece born from 40,000 stitches of gold-threaded contouring. High-grade silk meets liquid gold logic.",
                    image_filename="2d919111834f45fea5bbeee5b5f86d6b.jpg",
                    gallery_images="dragon_shirt_back.jpg,dragon_shirt_macro.jpg"),
            Product(name="Minimalist Gold Thread", category="Shirt", price=2500.0,
                    description="Elegant simplicity meets high-tech luxury. Subtle gold line work on pure black silk with a sculpted dragon collar pin.",
                    image_filename="2c77430db4e345f49148f23e5df3b5ea.jpg",
                    gallery_images="minimalist_shirt_back.jpg,minimalist_shirt_macro.jpg"),
            Product(name="Void Wave Trousers", category="Trousers", price=3000.0,
                    description="Structural minimalism designed by algorithms. Premium black wool-blend with fluid gold embroidery along the seam.",
                    image_filename="3cc9a3a935ce4233b07ec112d06594d9.jpg",
                    gallery_images="trousers_back.jpg,trousers_macro.jpg"),
            Product(name="Blood Dragon", category="Shirt", price=3800.0,
                    description="Three-headed dragon emblem in deep ruby crimson on midnight silk. A statement of ancestral power forged in metallic thread.",
                    image_filename="blood_dragon_front.jpg",
                    gallery_images="blood_dragon_back.jpg,blood_dragon_macro.jpg"),
            Product(name="Solar Tri-Dragon", category="Shirt", price=3800.0,
                    description="Three-headed dragon sigil in antique gold on obsidian silk. The ultimate fusion of heraldic art and digital-age precision.",
                    image_filename="solar_dragon_front.jpg",
                    gallery_images="solar_dragon_back.jpg,solar_dragon_macro.jpg"),
            Product(name="Crimson Wave Trousers", category="Trousers", price=3200.0,
                    description="Undulating fluid wave embroidery crafted in metallic ruby red thread along the tailored wool-blend silhouette. A dark luxury statement.",
                    image_filename="crimson_wave_front.jpg",
                    gallery_images="crimson_wave_back.jpg,crimson_wave_macro.jpg"),
            Product(name="Imperial Dragon Trousers", category="Trousers", price=3500.0,
                    description="Calligraphic dragon silhouette embroidered in fine gold thread along the right leg. Asymmetric bespoke tailoring in deep black wool-blend.",
                    image_filename="imperial_dragon_trousers_front.jpg",
                    gallery_images="imperial_dragon_trousers_back.jpg"),
            Product(name="Blood Dragon Trousers", category="Trousers", price=3500.0,
                    description="Minimalist dragon motif rendered in metallic crimson thread along the right leg. The definitive companion to the Blood Dragon shirt.",
                    image_filename="blood_dragon_trousers_front.jpg",
                    gallery_images="blood_dragon_trousers_back.jpg"),
        ]
        db.session.add_all(items)
        db.session.commit()

# --- ФУНКЦІЇ ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_telegram_message(message):
    global SENT_MESSAGES
    now = time.time()
    
    # ПЕРЕВІРКА: 3 секунди достатньо, щоб відсікти технічний дубль
    if message in SENT_MESSAGES and (now - SENT_MESSAGES[message]) < 3:
        print(f"--- [DEBUG] Дубль ігнорується ---")
        return
    
    SENT_MESSAGES[message] = now
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # PythonAnywhere free tier потребує проксі для зовнішніх запитів
    proxies = {'http': 'http://proxy.server:3128', 'https': 'http://proxy.server:3128'}
    
    try:
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, proxies=proxies, timeout=15)
        print(f"--- [DEBUG] Telegram Status: {response.status_code} ---")
    except Exception as e:
        print(f"--- [DEBUG] Telegram Error: {e} ---")

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
    return render_template("product_detail.html", product=product, images=product.all_images)

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
        current_time = time.time()
        last_submit = session.get('last_submit_time', 0)
        
        if current_time - last_submit < 5:
            session.pop("cart", None) 
            return redirect(url_for("success", reason="order"))
            
        session['last_submit_time'] = current_time
        
        try:
            name = request.form.get("name", "").strip()
            phone = request.form.get("phone", "").strip()
            city = request.form.get("city", "").strip()
            np = request.form.get("nova_poshta", "").strip()
            
            # Серверна валідація
            if not name or len(name) < 2 or len(name) > 120:
                return redirect(url_for("checkout"))
            if not phone or len(phone) < 10 or len(phone) > 20:
                return redirect(url_for("checkout"))
            if not city or len(city) < 2:
                return redirect(url_for("checkout"))
            if not np or len(np) < 3:
                return redirect(url_for("checkout"))
            
            summary = "\n".join([f"- {i.get('name')} ({i.get('size')})" for i in cart_items])
            
            order = Order(customer_name=name, customer_phone=phone, city=city, nova_poshta=np, items_summary=summary, total_price=total)
            db.session.add(order)
            db.session.commit()
            
            send_telegram_message(f"🔥 ЗАМОВЛЕННЯ 🔥\n👤 {name}\n📞 {phone}\n🏙 {city}\n📦 НП: {np}\n🛍 Товари:\n{summary}\n💰 {total} UAH")
            
            session.pop("cart", None)
            return redirect(url_for("success", reason="order"))
            
        except Exception as e:
            print(f"[ERROR] Checkout exception: {e}")
            return redirect(url_for("index"))
            
    return render_template("checkout.html", total=total, nova_poshta_api_key=NOVA_POSHTA_API_KEY)


@app.route("/subscribe", methods=["POST"])
def subscribe():
    current_time = time.time()
    last_sub = session.get('last_sub_time', 0)
    
    if current_time - last_sub < 3:
        return redirect(url_for("success", reason="subscribe"))
        
    session['last_sub_time'] = current_time
    email = request.form.get("email", "").strip().lower()
    
    # Валідація email формату
    if email and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        existing_lead = Lead.query.filter_by(email=email).first()
        
        if not existing_lead:
            db.session.add(Lead(email=email))
            db.session.commit()
            send_telegram_message(f"👤 New Waitlist Member: {email}")
        else:
            # Спеціально для твоїх тестів: шлемо сигнал, що клієнт "повернувся"
            send_telegram_message(f"👤 Returning Waitlist Member: {email}")

        return redirect(url_for("success", reason="subscribe"))
        
    return redirect(url_for("index"))
@app.route("/success")
def success():
    # Отримуємо причину з посилання, за замовчуванням 'order'
    reason = request.args.get('reason', 'order')
    return render_template("success.html", reason=reason)

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
    
    # Отримуємо всі дані
    orders = Order.query.all()
    leads = Lead.query.all()
    products = Product.query.all()
    
    # Економічні розрахунки
    total_revenue = sum(order.total_price for order in orders)
    order_count = len(orders)
    # Середній чек (уникаємо ділення на нуль)
    avg_check = total_revenue / order_count if order_count > 0 else 0
    
    return render_template("admin.html", 
                           orders=orders, 
                           leads=leads, 
                           products=products,
                           total_revenue=total_revenue,
                           order_count=order_count,
                           avg_check=avg_check)

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

@app.route("/admin/product/delete/<int:product_id>", methods=["POST"])
def admin_delete_product(product_id):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    db.session.delete(Product.query.get_or_404(product_id))
    db.session.commit()
    return redirect(url_for("admin_panel"))

@app.route("/admin/order/delete/<int:order_id>", methods=["POST"])
def admin_delete_order(order_id):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return redirect(url_for("admin_panel"))

@app.route("/admin/lead/delete/<int:lead_id>", methods=["POST"])
def admin_delete_lead(lead_id):
    if not session.get("admin_logged_in"): return redirect(url_for("admin_login"))
    lead = Lead.query.get_or_404(lead_id)
    db.session.delete(lead)
    db.session.commit()
    return redirect(url_for("admin_panel"))

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None); return redirect(url_for("admin_login"))

@app.context_processor
def inject_cart_count():
    cart = session.get("cart", [])
    return {"cart_count": len(cart)}

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

# --- СТАРТ ---
with app.app_context():
    UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
    db.create_all()
    seed_products() # ОЦЕ ПОВЕРНЕ ТВОЮ КОЛЕКЦІЮ
@app.route('/admin/update_status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    # 1. Отримуємо дані з "випадаючого списку" (select) в адмінці
    new_status = request.form.get('status')
    
    # 2. Шукаємо в базі даних замовлення саме за цим номером (id)
    order = Order.query.get(order_id)
    
    # 3. Перевірка: якщо таке замовлення існує
    if order:
        # Змінюємо старий статус на той, який ми обрали
        order.status = new_status
        
        # Записуємо зміни в базу (фінальне "Зберегти")
        db.session.commit()
        
        # Лог для тебе в консоль PythonAnywhere (щоб ти бачив, що все ок)
        print(f"Status for Order #{order_id} updated to {new_status}")
    
    # 4. Повертаємо тебе назад на сторінку адмінки, щоб не було білого екрану
    return redirect(url_for('admin_panel'))
if __name__ == "__main__":
    app.run(debug=True)