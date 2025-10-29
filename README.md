Rey&Hardy E‑commerce (Django)

Overview
- Brand: Rey&Hardy (Men, Women)
- Language/Currency: English, INR (₹)
- Categories: T‑shirts, Oversized T‑shirts
- Variants: Size (M, L, XL, XXL), Color (Red, Black, Navy Blue, White, Grey)
- Payments: Razorpay, Cash on Delivery
- Tax: GST included (configurable)
- Shipping: Shiprocket (placeholder), Pan‑India, Free above ₹399
- Returns: Within 7 days
- Checkout: Requires account login

Quick Start
1) Python env
   - Python 3.10+ recommended
   - Create venv and install deps:
     python -m venv .venv && source .venv/bin/activate
     pip install -r requirements.txt

2) Configure env
   - Copy .env.example to .env and fill values (SECRET_KEY, Razorpay keys):
     cp .env.example .env

3) Setup DB and admin
     python manage.py migrate
     python manage.py createsuperuser
     python manage.py seed_store
     # Optional richer dataset with images/reviews/coupons
     python manage.py seed_demo

4) Run
     python manage.py runserver

Admin Features
- Manage Categories, Products, Variants, Images
- Manage Orders and Items; view totals, status, tracking fields
- Manage Users (Django admin) and Profiles
- Manage Coupons (percent discounts)

Customer Features
- Registration/login (Email via allauth, plus Google when configured)
- Wishlist, Cart, Checkout (login required)
- Razorpay payment flow and COD option
- Order list, order detail with tracking number field
- Profile and saved address fields

Payments
- Razorpay: configure RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env
- The checkout creates a Razorpay order; payment is completed via hosted checkout.
- Callback URL: /payments/razorpay/callback/
- Webhook URL (optional): /payments/razorpay/webhook/

Shipping
- Orders include fields for provider (default Shiprocket) and tracking number.
- Shiprocket: configurable integration.
  - Auto-create shipments when an order becomes "paid" (Razorpay) and trigger from admin.
  - Configure env: set `SHIPROCKET_ENABLED=True`, `SHIPROCKET_EMAIL`, `SHIPROCKET_PASSWORD`, `SHIPROCKET_PICKUP_LOCATION` (must match your Shiprocket pickup location), optional `SHIPROCKET_CHANNEL_ID`.
  - Delivery charge at checkout: set `SHIPROCKET_PICKUP_PIN` to your origin PIN. If Shiprocket is enabled and customer address is known, the app estimates the cheapest courier rate between pickup and drop PINs and shows it as "Shipment Charge" under GST. Otherwise it falls back to flat/free shipping rules.
  - Defaults for weight/dimensions are configurable via env.
  - Admin action: in Orders list, select orders and run "Create Shiprocket shipment for selected orders".
  - Notes: For COD, shipments are not auto-created (status remains "created"). Use the admin action or update status to "paid" when appropriate.

GST & Currency
- Configure GST_RATE and CURRENCY_SYMBOL in .env (defaults: 0.18 and ₹).
- Free shipping threshold is FREE_SHIPPING_THRESHOLD (default: 399).

Google Login (optional)
- The project uses django-allauth. To enable Google sign-in:
  1) In Django admin > Social applications, add Google with client ID/secret.
  2) Set the site to match your domain (Sites framework).

Media & Images
- Upload product images via admin (stored under media/products/).
- Use high-quality images preferably on white backgrounds.

Domain & Branding
- Set SITE_DOMAIN in .env (e.g., Rey&Hardy.com).
- Update templates/base.html and navbar to include your logo and tagline.

Notes
- Database defaults to SQLite for local dev; switch to Postgres/MySQL in DATABASES for production.
- Ensure CSRF/HTTPS and proper allowed hosts in production.
