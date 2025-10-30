from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from catalog.models import Product, Variant, WishlistItem
from .models import Cart, CartItem
from .utils import (
    add_session_item,
    get_session_items,
    update_session_item as update_session_item_session,
    remove_session_item as remove_session_item_session,
    get_session_coupon,
    set_session_coupon,
    clear_session_coupon,
)
from coupons.models import Coupon
from accounts.models import Address
from orders.shiprocket import estimate_shipping_charge


def _get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def view_cart(request):
    is_auth = request.user.is_authenticated
    if is_auth and hasattr(request.user, "cart"):
        cart = _get_user_cart(request.user)
        db_items = list(cart.items.select_related("product", "variant"))
        cart_items = [
            {
                "db_item_id": it.id,
                "product": it.product,
                "variant": it.variant,
                "quantity": it.quantity,
                "unit_price": it.unit_price(),
                "line_total": it.line_total(),
            }
            for it in db_items
        ]
        subtotal = cart.subtotal()
    else:
        ses_items = get_session_items(request)
        cart_items = [
            {
                "db_item_id": None,
                "product": it.product,
                "variant": it.variant,
                "quantity": it.quantity,
                "unit_price": it.unit_price(),
                "line_total": it.line_total(),
            }
            for it in ses_items
        ]
        subtotal = sum((it["line_total"] for it in cart_items), Decimal("0.00"))
    # Coupon application
    coupon_code = get_session_coupon(request)
    coupon = None
    discount_amount = Decimal("0.00")
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code)
            if coupon.is_valid():
                discount_amount = (subtotal * Decimal(coupon.discount_percent) / Decimal("100")).quantize(Decimal("0.01"))
            else:
                coupon = None
        except Coupon.DoesNotExist:
            coupon = None

    discounted_subtotal = (subtotal - discount_amount).quantize(Decimal("0.01"))
    if discounted_subtotal < 0:
        discounted_subtotal = Decimal("0.00")

    gst_rate = Decimal(str(getattr(settings, "GST_RATE", "0.18")))
    gst_amount = (discounted_subtotal * gst_rate).quantize(Decimal("0.01"))
    # Dynamic shipping estimate when user has a default address; fallback to flat/free
    shipping = Decimal("0.00")
    if discounted_subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
        shipping = Decimal("0.00")
    else:
        ship_estimate = None
        if request.user.is_authenticated:
            try:
                addresses = Address.objects.filter(user=request.user)
                default_address = addresses.filter(is_default=True).first() or addresses.first()
                drop_pin = default_address.postal_code if default_address else None
                if drop_pin:
                    # Compute total weight and dims from cart items
                    total_w = Decimal("0.00")
                    max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
                    max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
                    max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
                    for it in (request.user.cart.items.select_related("product", "variant") if hasattr(request.user, "cart") else []):
                        w = None
                        if it.variant and getattr(it.variant, "weight_kg", None):
                            w = Decimal(str(it.variant.weight_kg))
                        elif getattr(it.product, "weight_kg", None):
                            w = Decimal(str(it.product.weight_kg))
                        else:
                            w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
                        total_w += (w * Decimal(it.quantity))
                        lv = (getattr(it.variant, "length_cm", None) if it.variant else None) or getattr(it.product, "length_cm", None)
                        bv = (getattr(it.variant, "breadth_cm", None) if it.variant else None) or getattr(it.product, "breadth_cm", None)
                        hv = (getattr(it.variant, "height_cm", None) if it.variant else None) or getattr(it.product, "height_cm", None)
                        if lv:
                            try: max_l = max(max_l, int(lv))
                            except Exception: pass
                        if bv:
                            try: max_b = max(max_b, int(bv))
                            except Exception: pass
                        if hv:
                            try: max_h = max(max_h, int(hv))
                            except Exception: pass
                    units_total = sum((it["quantity"] for it in cart_items), 0)
                    est = estimate_shipping_charge(
                        drop_pin=str(drop_pin),
                        units_total=units_total or 1,
                        cod=False,
                        declared_value=discounted_subtotal,
                        total_weight_kg=total_w,
                        dims_cm=(max_l, max_b, max_h),
                    )
                    ship_estimate = est
            except Exception:
                ship_estimate = None
        if ship_estimate is not None:
            shipping = ship_estimate.quantize(Decimal("0.01"))
        else:
            flat = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))
            shipping = flat
    total = (discounted_subtotal + gst_amount + shipping).quantize(Decimal("0.01"))

    # Saved for later (wishlist) items for authenticated users
    saved_items = []
    if request.user.is_authenticated:
        try:
            qs = WishlistItem.objects.filter(user=request.user).select_related("product").prefetch_related("product__images")
            for w in qs:
                img_url = None
                try:
                    img_obj = w.product.images.first()
                    img_url = img_obj.image.url if img_obj else None
                except Exception:
                    img_url = None
                # compute display price
                price = w.product.price()
                old_price = w.product.base_price if (w.product.sale_price is not None) else None
                saved_items.append({
                    "product": w.product,
                    "img": img_url,
                    "link": f"/product/{w.product.slug}/",
                    "price": price,
                    "old_price": old_price,
                })
        except Exception:
            saved_items = []

    return render(
        request,
        "cart/view_cart.html",
        {
            "cart_items": cart_items,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "discounted_subtotal": discounted_subtotal,
            "coupon": coupon,
            "coupon_code": coupon_code,
            "gst_amount": gst_amount,
            "shipping": shipping,
            "total": total,
            "saved_items": saved_items,
        },
    )


def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size = request.POST.get("size")
    color = request.POST.get("color")
    variant = None
    if product.variants.exists():
        variant = get_object_or_404(product.variants, size=size, color=color)

    qty = int(request.POST.get("quantity", 1))
    # Buy Now flow: skip adding to cart, store as temporary session item
    if request.POST.get("buy_now") == "1":
        request.session["buy_now"] = {
            "product_id": product.id,
            "variant_id": (variant.id if variant else None),
            "quantity": qty,
        }
        request.session.modified = True
        return redirect("checkout")

    # Regular add to cart
    if request.user.is_authenticated:
        cart = _get_user_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant)
        if not created:
            item.quantity += qty
        else:
            item.quantity = qty
        item.save()
    else:
        add_session_item(request, product.id, variant.id if variant else None, qty)
    # Remember last picked variant for this product (to reuse when moving from saved)
    try:
        lv = request.session.get('last_variant', {})
        key = str(product.id)
        lv[key] = (variant.id if variant else None)
        request.session['last_variant'] = lv
        request.session.modified = True
    except Exception:
        pass
    messages.success(request, "Added to cart")
    return redirect("view_cart")


def update_cart_item(request, item_id):
    qty = max(1, int(request.POST.get("quantity", 1)))
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")

    # Defaults for response
    resp = {"ok": True, "pid": None, "vid": None}

    if request.user.is_authenticated:
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
            item.quantity = qty
            item.save()
            product = item.product
            variant = item.variant
            resp.update({
                "pid": product.id,
                "vid": variant.id if variant else None,
                "item_total": str(item.line_total().quantize(Decimal("0.01"))),
            })
        except CartItem.DoesNotExist:
            # fallback to session
            pid = int(request.POST.get("product_id"))
            vid_raw = request.POST.get("variant_id")
            vid = int(vid_raw) if vid_raw not in (None, "", "None") else None
            update_session_item_session(request, pid, vid, qty)
            product = get_object_or_404(Product, id=pid)
            variant = Variant.objects.filter(id=vid).first() if vid else None
            line_total = product.price() * qty
            resp.update({"pid": pid, "vid": vid, "item_total": str(line_total.quantize(Decimal("0.01")))})
    else:
        pid = int(request.POST.get("product_id"))
        vid_raw = request.POST.get("variant_id")
        vid = int(vid_raw) if vid_raw not in (None, "", "None") else None
        update_session_item_session(request, pid, vid, qty)
        product = get_object_or_404(Product, id=pid)
        variant = Variant.objects.filter(id=vid).first() if vid else None
        line_total = product.price() * qty
        resp.update({"pid": pid, "vid": vid, "item_total": str(line_total.quantize(Decimal("0.01")))})

    # Compute cart totals & count
    gst_rate = Decimal(str(getattr(settings, "GST_RATE", "0.18")))
    flat = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))

    if request.user.is_authenticated and hasattr(request.user, "cart"):
        cart = request.user.cart
        subtotal = cart.subtotal()
        cart_count = sum((it.quantity for it in cart.items.all()), 0)
    else:
        ses_items = get_session_items(request)
        subtotal = sum((it.line_total() for it in ses_items), Decimal("0.00"))
        cart_count = sum((it.quantity for it in ses_items), 0)

    gst_amount = (subtotal * gst_rate).quantize(Decimal("0.01"))
    # Try dynamic estimate for authenticated users with a default address
    if subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
        shipping = Decimal("0.00")
    else:
        ship_estimate = None
        try:
            if request.user.is_authenticated:
                addresses = Address.objects.filter(user=request.user)
                default_address = addresses.filter(is_default=True).first() or addresses.first()
                drop_pin = default_address.postal_code if default_address else None
                if drop_pin and hasattr(request.user, "cart"):
                    total_w = Decimal("0.00")
                    max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
                    max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
                    max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
                    for it in request.user.cart.items.select_related("product", "variant"):
                        if it.variant and getattr(it.variant, "weight_kg", None):
                            w = Decimal(str(it.variant.weight_kg))
                        elif getattr(it.product, "weight_kg", None):
                            w = Decimal(str(it.product.weight_kg))
                        else:
                            w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
                        total_w += (w * Decimal(it.quantity))
                        lv = (getattr(it.variant, "length_cm", None) if it.variant else None) or getattr(it.product, "length_cm", None)
                        bv = (getattr(it.variant, "breadth_cm", None) if it.variant else None) or getattr(it.product, "breadth_cm", None)
                        hv = (getattr(it.variant, "height_cm", None) if it.variant else None) or getattr(it.product, "height_cm", None)
                        if lv:
                            try: max_l = max(max_l, int(lv))
                            except Exception: pass
                        if bv:
                            try: max_b = max(max_b, int(bv))
                            except Exception: pass
                        if hv:
                            try: max_h = max(max_h, int(hv))
                            except Exception: pass
                    units_total = sum((it.quantity for it in request.user.cart.items.all()), 0)
                    est = estimate_shipping_charge(
                        drop_pin=str(drop_pin),
                        units_total=units_total or 1,
                        cod=False,
                        declared_value=subtotal,
                        total_weight_kg=total_w,
                        dims_cm=(max_l, max_b, max_h),
                    )
                    ship_estimate = est
        except Exception:
            ship_estimate = None

        if ship_estimate is not None:
            shipping = Decimal(ship_estimate).quantize(Decimal("0.01"))
        else:
            shipping = flat
    total = (subtotal + gst_amount + shipping).quantize(Decimal("0.01"))

    resp.update({
        "subtotal": str(subtotal),
        "gst_amount": str(gst_amount),
        "shipping": str(shipping),
        "total": str(total),
        "cart_count": cart_count,
    })

    if is_ajax:
        return JsonResponse(resp)
    return redirect("view_cart")


def remove_cart_item(request, item_id):
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")
    pid = int(request.GET.get("product_id", 0)) or int(request.POST.get("product_id", 0)) if (request.method == "POST" or request.method == "GET") else 0
    vraw = request.GET.get("variant_id") or request.POST.get("variant_id")
    vid = int(vraw) if vraw not in (None, "", "None") else None

    if request.user.is_authenticated:
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
            pid = item.product.id
            vid = item.variant.id if item.variant else None
            item.delete()
        except CartItem.DoesNotExist:
            remove_session_item_session(request, pid, vid)
    else:
        remove_session_item_session(request, pid, vid)

    # Compute updated totals and count
    gst_rate = Decimal(str(getattr(settings, "GST_RATE", "0.18")))
    flat = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))
    if request.user.is_authenticated and hasattr(request.user, "cart"):
        cart = request.user.cart
        subtotal = cart.subtotal()
        cart_count = sum((it.quantity for it in cart.items.all()), 0)
    else:
        ses_items = get_session_items(request)
        subtotal = sum((it.line_total() for it in ses_items), Decimal("0.00"))
        cart_count = sum((it.quantity for it in ses_items), 0)
    gst_amount = (subtotal * gst_rate).quantize(Decimal("0.01"))
    shipping = Decimal("0.00") if subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)) else flat
    total = (subtotal + gst_amount + shipping).quantize(Decimal("0.01"))

    if is_ajax:
        return JsonResponse({
            "ok": True,
            "pid": pid,
            "vid": vid,
            "subtotal": str(subtotal),
            "gst_amount": str(gst_amount),
            "shipping": str(shipping),
            "total": str(total),
            "cart_count": cart_count,
        })

    messages.info(request, "Removed item from cart")
    return redirect("view_cart")


def save_for_later(request, item_id):
    # Requires authentication to use wishlist
    if not request.user.is_authenticated:
        messages.info(request, "Sign in to save items for later.")
        return redirect("view_cart")
    # Try database cart item
    try:
        item = CartItem.objects.get(id=item_id, cart__user=request.user)
        WishlistItem.objects.get_or_create(user=request.user, product=item.product)
        # store last variant choice
        try:
            lv = request.session.get('last_variant', {})
            lv[str(item.product.id)] = (item.variant.id if item.variant else None)
            request.session['last_variant'] = lv
            request.session.modified = True
        except Exception:
            pass
        item.delete()
        messages.success(request, "Saved for later")
        return redirect("view_cart")
    except CartItem.DoesNotExist:
        # Fallback: session cart item via product/variant ids
        try:
            pid = int(request.GET.get("product_id"))
        except Exception:
            pid = 0
        vraw = request.GET.get("variant_id")
        vid = int(vraw) if vraw not in (None, "", "None") else None
        if pid:
            try:
                product = Product.objects.get(id=pid)
                WishlistItem.objects.get_or_create(user=request.user, product=product)
            except Product.DoesNotExist:
                pass
            # Remove from session cart
            remove_session_item_session(request, pid, vid)
            # store last variant for session save
            try:
                lv = request.session.get('last_variant', {})
                lv[str(pid)] = vid
                request.session['last_variant'] = lv
                request.session.modified = True
            except Exception:
                pass
            messages.success(request, "Saved for later")
        return redirect("view_cart")


def move_saved_to_cart(request, product_id: int):
    if not request.user.is_authenticated:
        messages.info(request, "Sign in to move items to cart.")
        return redirect("view_cart")
    product = get_object_or_404(Product, id=product_id, is_active=True)
    # Remove from wishlist entry
    WishlistItem.objects.filter(user=request.user, product=product).delete()
    # If product has variants, try last_variant mapping
    if product.variants.exists():
        try:
            lv = request.session.get('last_variant', {})
            vid = lv.get(str(product.id))
            variant = None
            if vid not in (None, '', '0', 0, 'None'):
                variant = Variant.objects.filter(id=int(vid), product=product).first()
            if not variant:
                messages.info(request, "Select size and color before adding to cart.")
                return redirect("product_detail", slug=product.slug)
        except Exception:
            messages.info(request, "Select size and color before adding to cart.")
            return redirect("product_detail", slug=product.slug)
    # Add to cart directly
    cart = _get_user_cart(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=(variant if product.variants.exists() else None))
    if not created:
        item.quantity += 1
    else:
        item.quantity = 1
    item.save()
    messages.success(request, "Moved to cart")
    return redirect("view_cart")


def checkout_selected(request):
    if request.method != "POST":
        return redirect("view_cart")
    sels = request.POST.getlist("sel")
    if not sels:
        messages.info(request, "Select at least one item to proceed.")
        return redirect("view_cart")
    selected = {"auth": request.user.is_authenticated, "db_ids": [], "sv": []}
    for s in sels:
        try:
            if s.startswith("db:"):
                sid = int(s.split(":", 1)[1])
                selected["db_ids"].append(sid)
            elif s.startswith("sv:"):
                _, pid, vid = s.split(":", 2)
                pid_i = int(pid)
                vid_i = int(vid) if vid not in ("", "0", "None", None) else None
                # Find current qty from session cart
                qty = 1
                for it in get_session_items(request):
                    if it.product.id == pid_i and ((it.variant.id if it.variant else None) == vid_i):
                        qty = it.quantity
                        break
                selected["sv"].append({"pid": pid_i, "vid": vid_i, "qty": qty})
        except Exception:
            continue
    if not selected["db_ids"] and not selected["sv"]:
        messages.info(request, "Select at least one item to proceed.")
        return redirect("view_cart")
    # Persist selection for checkout and ensure buy-now is cleared
    request.session["checkout_selected"] = selected
    request.session.pop("buy_now", None)
    request.session.modified = True
    return redirect("checkout")


def apply_coupon(request):
    code = (request.POST.get("coupon", "") or request.GET.get("coupon", "")).strip()
    if not code:
        messages.error(request, "Enter a coupon code")
        return redirect("view_cart")
    try:
        coupon = Coupon.objects.get(code__iexact=code)
        if not coupon.is_valid():
            messages.error(request, "Coupon is not active")
        else:
            set_session_coupon(request, coupon.code)
            messages.success(request, f"Coupon '{coupon.code}' applied")
    except Coupon.DoesNotExist:
        messages.error(request, "Invalid coupon code")
    return redirect("view_cart")


def remove_coupon(request):
    clear_session_coupon(request)
    messages.info(request, "Coupon removed")
    return redirect("view_cart")
