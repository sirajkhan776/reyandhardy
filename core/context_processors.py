from decimal import Decimal
from django.conf import settings
from django.db import models


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

    # default/saved addresses for quick mobile header location selector
    default_address = None
    user_addresses = []
    wishlist_count = 0
    try:
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            from accounts.models import Address  # local import to avoid early app load
            from catalog.models import WishlistItem
            from accounts.models import Notification, NotificationRead
            user_addresses = list(Address.objects.filter(user=user).all())
            if user_addresses:
                default_address = next((a for a in user_addresses if a.is_default), None) or user_addresses[0]
            try:
                wishlist_count = int(WishlistItem.objects.filter(user=user).count())
            except Exception:
                wishlist_count = 0
            try:
                # Unread = active (broadcast or to user) without read receipt
                notif_qs = Notification.objects.filter(is_active=True).filter(models.Q(user__isnull=True) | models.Q(user=user)).order_by('-created_at')
                notif_ids = list(notif_qs.values_list('id', flat=True))
                read_ids = set(NotificationRead.objects.filter(user=user, notification_id__in=notif_ids).values_list('notification_id', flat=True))
                unread = sum(1 for nid in notif_ids if nid not in read_ids)
                latest = list(notif_qs[:5])
                total_count = len(notif_ids)
            except Exception:
                unread = 0
                latest = []
                total_count = 0
        else:
            unread = 0
            latest = []
            total_count = 0
    except Exception:
        default_address = None
        user_addresses = []
        unread = 0
        latest = []
        total_count = 0

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
        "DEFAULT_ADDRESS": default_address,
        "USER_ADDRESSES": user_addresses,
        "WISHLIST_COUNT": wishlist_count,
        "NOTIF_COUNT": unread,
        "NOTIF_LATEST": latest,
        "NOTIF_READ_IDS": list(read_ids) if 'read_ids' in locals() else [],
        "NOTIF_TOTAL": total_count,
    }
