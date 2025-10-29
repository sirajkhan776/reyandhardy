from decimal import Decimal
from django.conf import settings


def store_context(request):
    # derive cart count for mobile bottom nav
    cart_count = 0
    try:
        if getattr(request, "user", None) and request.user.is_authenticated and hasattr(request.user, "cart"):
            cart = request.user.cart
            cart_count = sum((it.quantity for it in cart.items.all()), 0)
        else:
            from cart.utils import get_session_items  # local import avoids app load order issues
            cart_count = sum((it.quantity for it in get_session_items(request)), 0)
    except Exception:
        cart_count = 0

    # load categories for mobile menu
    try:
        from catalog.models import Category  # local import to avoid early app load
        all_categories = list(Category.objects.all().only("name", "slug"))
    except Exception:
        all_categories = []

    return {
        "STORE_NAME": getattr(settings, "STORE_NAME", "Store"),
        "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "₹"),
        "GST_RATE": Decimal(str(getattr(settings, "GST_RATE", "0.18"))),
        "GSTIN": getattr(settings, "GSTIN", ""),
        "FREE_SHIPPING_THRESHOLD": getattr(settings, "FREE_SHIPPING_THRESHOLD", 399),
        "BRAND_TAGLINE": getattr(settings, "BRAND_TAGLINE", ""),
        "BRAND_LOGO": getattr(settings, "BRAND_LOGO", "img/logo.svg"),
        "BRAND_GOLD": getattr(settings, "BRAND_GOLD", ""),
        "BRAND_GOLD_DARK": getattr(settings, "BRAND_GOLD_DARK", ""),
        "CART_COUNT": cart_count,
        "ALL_CATEGORIES": all_categories,
    }
