import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    SECRET_KEY=(str, "change-me"),
    ALLOWED_HOSTS=(list, ["*"]),
    GST_RATE=(str, "0.18"),
    GSTIN=(str, ""),
    FREE_SHIPPING_THRESHOLD=(int, 399),
    FLAT_SHIPPING_RATE=(int, 49),
    CURRENCY_SYMBOL=(str, "₹"),
    RAZORPAY_KEY_ID=(str, "rzp_test_RYzoS25zC78s7C"),
    RAZORPAY_KEY_SECRET=(str, "Ivb4hWA6SU00EPh9MZW1pKgC"),
    SITE_DOMAIN=(str, "reyhardy.com"),
    BRAND_TAGLINE=(str, "Premium T-shirts for Men & Women"),
    BRAND_LOGO=(str, "img/logo1.png"),
    BRAND_GOLD=(str, "#d4af37"),
    BRAND_GOLD_DARK=(str, "#b8860b"),
    # Shiprocket
    SHIPROCKET_ENABLED=(bool, False),
    SHIPROCKET_EMAIL=(str, ""),
    SHIPROCKET_PASSWORD=(str, ""),
    SHIPROCKET_PICKUP_LOCATION=(str, ""),
    SHIPROCKET_CHANNEL_ID=(str, ""),
    SHIPROCKET_PICKUP_PIN=(str, ""),
    SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG=(float, 0.5),
    SHIPROCKET_DEFAULT_DIM_LCM=(int, 20),
    SHIPROCKET_DEFAULT_DIM_BCM=(int, 15),
    SHIPROCKET_DEFAULT_DIM_HCM=(int, 2),
    # Analytics: estimated cost of goods as a fraction of net sales (0.0-1.0)
    COGS_RATE=(float, 0.0),
)

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))

DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Ensure Render deployment hostname is allowed and trusted for CSRF
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    # Add host (no scheme) to ALLOWED_HOSTS
    if isinstance(ALLOWED_HOSTS, (list, tuple)):
        if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
            ALLOWED_HOSTS = list(ALLOWED_HOSTS) + [RENDER_EXTERNAL_HOSTNAME]
    elif isinstance(ALLOWED_HOSTS, str):
        # In case misconfigured as a string, convert to list
        ALLOWED_HOSTS = [ALLOWED_HOSTS, RENDER_EXTERNAL_HOSTNAME]
    else:
        ALLOWED_HOSTS = [RENDER_EXTERNAL_HOSTNAME]

    # CSRF trusted origins require scheme + host
    _csrf_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"
    try:
        CSRF_TRUSTED_ORIGINS  # may or may not exist yet
    except NameError:
        CSRF_TRUSTED_ORIGINS = []
    if _csrf_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS = list(CSRF_TRUSTED_ORIGINS) + [_csrf_origin]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    # Third-party
    "widget_tweaks",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    # Local apps (explicit AppConfig to avoid name conflicts)
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "catalog.apps.CatalogConfig",
    "cart.apps.CartConfig",
    "orders.apps.OrdersConfig",
    "payments.apps.PaymentsConfig",
    "reviews.apps.ReviewsConfig",
    "coupons.apps.CouponsConfig",
    "dashboard.apps.DashboardConfig",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "reyhardy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.store_context",
            ],
        },
    },
]

WSGI_APPLICATION = "reyhardy.wsgi.application"

# Authentication (django-allauth)
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Dev email backend
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Database: use DATABASE_URL if provided (e.g., Render Postgres), fallback to SQLite
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Persistent connections (no-op for SQLite)
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Allauth configuration (email login + Google)
# New-style settings to avoid deprecation warnings.
ACCOUNT_LOGIN_METHODS = {"email", "username"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "optional"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Store settings
STORE_NAME = "Rey&Hardy"
STORE_DOMAIN = env("SITE_DOMAIN")
CURRENCY_SYMBOL = env("CURRENCY_SYMBOL")
GST_RATE = env("GST_RATE")  # as string Decimal
GSTIN = env("GSTIN")
FREE_SHIPPING_THRESHOLD = env("FREE_SHIPPING_THRESHOLD")
FLAT_SHIPPING_RATE = env("FLAT_SHIPPING_RATE")
BRAND_TAGLINE = env("BRAND_TAGLINE")
BRAND_LOGO = env("BRAND_LOGO")  # relative to STATIC files, e.g., img/logo.png
BRAND_GOLD = env("BRAND_GOLD")
BRAND_GOLD_DARK = env("BRAND_GOLD_DARK")

# Razorpay keys
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")

# Shiprocket
SHIPROCKET_ENABLED = env("SHIPROCKET_ENABLED")
SHIPROCKET_EMAIL = env("SHIPROCKET_EMAIL")
SHIPROCKET_PASSWORD = env("SHIPROCKET_PASSWORD")
SHIPROCKET_PICKUP_LOCATION = env("SHIPROCKET_PICKUP_LOCATION")
SHIPROCKET_CHANNEL_ID = env("SHIPROCKET_CHANNEL_ID")
SHIPROCKET_PICKUP_PIN = env("SHIPROCKET_PICKUP_PIN")
SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG = env("SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG")
SHIPROCKET_DEFAULT_DIM_LCM = env("SHIPROCKET_DEFAULT_DIM_LCM")
SHIPROCKET_DEFAULT_DIM_BCM = env("SHIPROCKET_DEFAULT_DIM_BCM")
SHIPROCKET_DEFAULT_DIM_HCM = env("SHIPROCKET_DEFAULT_DIM_HCM")

# Analytics / profit estimation
COGS_RATE = env("COGS_RATE")
