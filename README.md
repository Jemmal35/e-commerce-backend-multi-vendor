# Multi-Vendor E-Commerce Backend

A production-grade, highly scalable multi-vendor e-commerce backend built with **Django** and **Django REST Framework (DRF)**. It features robust vendor-specific product and order management, secure Stripe payment processing, advanced full-text search capabilities, and optimized vendor analytics.

---

## 🚀 Key Features

* **Multi-Vendor Architecture**: Isolated vendor accounts, store management, and vendor-specific product/catalog operations.
* **Product Management & Variants**: Support for parent products, attributes, SKUs, and stock tracking via `ProductVariant`.
* **Advanced Analytics Engine**: High-performance database annotations (`Count`, `Sum`, `Q`) to calculate order metrics and units sold directly at the database layer (avoiding N+1 query bottlenecks).
* **Robust Search Engine**: Full-text search engine utilizing PostgreSQL `SearchVector` and `SearchRank`, with an intelligent conditional fallback to `icontains` for local SQLite development.
* **Stripe Payment Integration**: Secure checkout processing handling precise cent-to-decimal calculations (`Decimal('100')`) and webhook lifecycle states.
* **Order & Dispute Management**: Complete order tracking lifecycle (`Pending`, `Paid`, `Processing`, `Shipped`, `Delivered`, `Cancelled`, `Refunded`) and dispute resolution modules.
* **Background Processing**: Asynchronous task scheduling configured with Celery and Celery Beat.

---

## 🛠️ Tech Stack

* **Core:** Python 3.12, Django 6.0, Django REST Framework (DRF)
* **Database:** PostgreSQL (Production), SQLite (Local Development Fallback)
* **Payments:** Stripe API
* **Task Queue:** Celery, Redis, Celery Beat
* **Containerization:** Docker & Docker Compose

---

## 📦 Project Structure

```text
src/
├── apps/
│   ├── cart/         # Shopping cart & coupons
│   ├── catalog/      # Products, variants, categories, search engine
│   ├── orders/       # Orders, order items, status management
│   ├── payments/     # Stripe integration & payment statuses
│   ├── vendors/      # Vendor profiles, dashboard analytics, endpoints
│   └── disputes/     # Order dispute management
├── config/           # Django project settings, wsgi, asgi, urls
└── manage.py



⚙️ Getting Started
Prerequisites
Python 3.12+

Docker & Docker Compose (Recommended)

PostgreSQL (or use SQLite for quick local setup)

Installation & Setup
Clone the repository:

Bash
git clone [https://github.com/Jemmal35/e-commerce-backend-multi-vendor.git](https://github.com/Jemmal35/e-commerce-backend-multi-vendor.git)
cd e-commerce-backend-multi-vendor
Create and activate a virtual environment:

Bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Install dependencies:

Bash
pip install -r requirements.txt
Configure Environment Variables:
Create a .env file in the root directory based on your configuration needs:

Code snippet
DEBUG=True
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
Run Database Migrations:

Bash
python src/manage.py migrate
Start the Development Server:

Bash
python src/manage.py runserver
🐳 Running with Docker
To run the complete containerized stack (Web, Database, Redis, Celery):

Bash
docker-compose up --build

Run migrations inside the container (in a new terminal tab):

Bash
docker-compose exec web python src/manage.py migrate