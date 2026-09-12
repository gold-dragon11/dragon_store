# Shadow of the Dragon (Dragon Store)

> A luxury digital-to-order menswear e-commerce platform built with Flask.

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-ORM-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)

---

## Overview

**Shadow of the Dragon** is a high-end menswear e-commerce platform designed with a contemporary digital-to-order atelier ethos. Rejecting fast-fashion overproduction, each garment is tailored on demand to eliminate deadstock and guarantee meticulous craftsmanship.

The platform couples a bespoke dark luxury visual identity—featuring gold accents, smooth scroll transitions via AOS.js, and a refined pairing of *Cinzel* and *Montserrat* typography—with a resilient, production-ready Flask architecture deployed on PythonAnywhere.

---

## Key Features

### E-Commerce Flow
- **End-to-End Shopping Experience**: Intuitive customer journey spanning product discovery (catalog) &rarr; detailed item inspection &rarr; session-based shopping cart &rarr; address-aware checkout &rarr; confirmation screen.
- **Made-to-Order Philosophy**: Sustainable digital-to-order production model with on-demand fulfillment, eliminating warehouse surplus.
- **Smart Logistics (Nova Poshta API)**: Client-side integration with the Ukrainian Nova Poshta postal service offering instant city autocomplete and dynamic branch / parcel locker search.

### Administrative Operations & Analytics
- **Product Catalog CRUD**: Secure administrator dashboard to create, update, view, and delete garments with custom image upload handling.
- **Order Management & Status Tracking**: Real-time order monitoring with dynamic fulfillment lifecycle updates (`NEW`, `IN_PRODUCTION`, `SHIPPED`, `COMPLETED`).
- **Revenue Dashboard**: Real-time business KPIs summarizing total revenue, total order volume, and calculated average check value.
- **Waitlist & Lead Capture**: Dedicated waitlist subscription engine tracking interested clientele for upcoming capsule drops.

### Integrations & Infrastructure
- **Telegram Bot Notifications**: Instant dispatch of real-time alerts to the store operator for incoming orders and waitlist submissions.
- **Duplicate Prevention**: Client- and server-side debounce logic preventing accidental duplicate orders or repeated Telegram notifications.
- **Server-Side Validation**: Robust input sanitization, form validation, and secure file handling using Werkzeug.
- **Environment Isolation**: Secure separation of application credentials, API keys, and secrets via `python-dotenv`.

---

## Tech Stack

| Category | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python 3.13 / Flask 3.1 | Application routing, controllers, session handling |
| **Database & ORM** | SQLite / Flask-SQLAlchemy | Relational database modeling and persistence |
| **Templating** | Jinja2 | Dynamic server-side page rendering and component reuse |
| **Styling & UI** | Custom CSS3 | Dark luxury aesthetics, gold accent highlights, responsive layout |
| **Typography** | Google Fonts | *Cinzel* (luxury serif headers) & *Montserrat* (clean sans-serif body) |
| **Animations** | AOS.js | Smooth scroll-triggered entrance animations |
| **Messaging** | Telegram Bot API | Administrator notifications for orders and lead capture |
| **Logistics** | Nova Poshta API | Dynamic Ukrainian postal city autocomplete and branch finder |
| **Configuration** | python-dotenv | Local & production environment variable management |
| **Hosting** | PythonAnywhere | Cloud deployment environment |

---

## Project Structure

```text
dragon_store/
├── app.py                      # Main Flask application (routes, models, admin logic, APIs)
├── requirements.txt            # Python dependencies and pinned versions
├── .env                        # Local environment variables & secrets (excluded from Git)
├── static/
│   ├── css/
│   │   └── style.css           # Custom stylesheets and design system
│   └── images/                 # Product imagery and user-uploaded media
└── templates/                  # Jinja2 HTML templates
    ├── base.html               # Master layout (navigation bar, footer, shared assets)
    ├── index.html              # Hero landing page, brand narrative & catalog showcase
    ├── product_detail.html     # Dedicated product page with size selection
    ├── cart.html               # Interactive cart summary and quantity management
    ├── checkout.html           # Shipping details and Nova Poshta API integration
    ├── success.html            # Confirmation view for orders and newsletter signups
    ├── admin_login.html        # Secure administrative login portal
    ├── admin.html              # Admin dashboard (CRUD, order pipeline, revenue KPIs)
    └── 404.html                # Custom styled error page
```

---

## Getting Started Locally

Follow these steps to set up and run the project in your local development environment.

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/dragon-store.git
cd dragon-store
```

### 2. Install Dependencies
Create and activate a virtual environment, then install the required Python packages:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:

```env
SECRET_KEY=your_secure_secret_key_here
ADMIN_PASSWORD=your_admin_panel_password
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### 4. Run the Application
Launch the Flask development server:

```bash
python app.py
```

### 5. Access the Platform
- **Storefront**: Open [http://localhost:5000](http://localhost:5000) in your web browser.
- **Admin Dashboard**: Open [http://localhost:5000/admin](http://localhost:5000/admin) and log in with your configured `ADMIN_PASSWORD`.

---

## Screenshots

> *Note: Section placeholders for visual portfolio documentation. Replace notes with actual screenshot paths or demo GIFs.*

### Storefront & Hero Showcase
<!-- Placeholder: Add desktop & mobile storefront screenshots here -->
*Landing page showcasing the dark luxury aesthetic, brand story, and interactive product gallery.*

### Product Detail View
<!-- Placeholder: Add product detail screenshot here -->
*Product page detailing garment craftsmanship, fabric specifications, and size selectors.*

### Cart & Nova Poshta Checkout
<!-- Placeholder: Add cart and checkout flow screenshots here -->
*Frictionless checkout featuring real-time Ukrainian city autocomplete and branch/locker lookup.*

### Admin Dashboard & Revenue Analytics
<!-- Placeholder: Add admin dashboard screenshot here -->
*Operational dashboard displaying revenue totals, average order value, order tracking, and product CRUD.*

### Telegram Bot Notifications
<!-- Placeholder: Add Telegram bot screenshot here -->
*Instant Telegram alerts dispatched to administrators upon new orders and waitlist registrations.*

---

## Architectural Highlights

- **Sustainable Digital-to-Order Model**: Minimizes textile waste by structuring catalog items for made-to-order fulfillment rather than traditional batch pre-orders.
- **Debounced Webhook Dispatch**: Protects external communication channels against network retries and duplicate form submissions with timestamp-based throttling.
- **Integrated Postal Search**: Reduces checkout abandonment by streamlining address entry with asynchronous queries against Nova Poshta's JSON API endpoints.
