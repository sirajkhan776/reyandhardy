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
        cart_items = []
        def _thumb_for(product, color: str):
            try:
                imgs = list(getattr(product, "images", None).all()) if getattr(product, "images", None) else []
                if color:
                    low = str(color).strip().lower()
                    for im in imgs:
                        c = (getattr(im, "color", "") or "").strip().lower()
                        if c and c == low and getattr(im, "image", None) and getattr(im.image, "url", None):
                            return im.image.url
                if imgs:
                    im0 = imgs[0]
                    if getattr(im0, "image", None) and getattr(im0.image, "url", None):
                        return im0.image.url
            except Exception:
                return ""
            return ""
        for it in db_items:
            try:
                size_options = list({v.size for v in it.product.variants.all()})
            except Exception:
                size_options = []
            color = (getattr(it.variant, "color", None) or "") if it.variant else ""
            cart_items.append({
                "db_item_id": it.id,
                "product": it.product,
                "variant": it.variant,
                "quantity": it.quantity,
                "unit_price": it.unit_price(),
                "line_total": it.line_total(),
                "size_options": size_options,
                "thumb_url": _thumb_for(it.product, color),
            })
        subtotal = cart.subtotal()
    else:
        ses_items = get_session_items(request)
        cart_items = []
        for it in ses_items:
            try:
                size_options = list({v.size for v in it.product.variants.all()})
            except Exception:
                size_options = []
            color = (getattr(it.variant, "color", None) or "") if it.variant else ""
            cart_items.append({
                "db_item_id": None,
                "product": it.product,
                "variant": it.variant,
                "quantity": it.quantity,
                "unit_price": it.unit_price(),
                "line_total": it.line_total(),
                "size_options": size_options,
                "thumb_url": _thumb_for(it.product, color),
            })
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
    # Dynamic shipping estimate using session delivery pin (if set) or default address; fallback to flat/free
    shipping = Decimal("0.00")
    if discounted_subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
        shipping = Decimal("0.00")
    else:
        ship_estimate = None
        try:
            delivery = request.session.get("delivery") or {}
            drop_pin = (str(delivery.get("postal_code") or "").strip() or None)
            if not drop_pin and request.user.is_authenticated:
                addresses = Address.objects.filter(user=request.user)
                default_address = addresses.filter(is_default=True).first() or addresses.first()
                drop_pin = default_address.postal_code if default_address else None
            if drop_pin:
                # Compute total weight and dims from cart items (db for auth, session list for guests)
                total_w = Decimal("0.00")
                max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
                max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
                max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
                if request.user.is_authenticated and hasattr(request.user, "cart"):
                    items_iter = request.user.cart.items.select_related("product", "variant")
                else:
                    # Build a light-weight iterable from current view cart_items
                    class _Wrap: pass
                    items_iter = []
                    for c in cart_items:
                        w = _Wrap()
                        w.product = c["product"]
                        w.variant = c["variant"]
                        w.quantity = c["quantity"]
                        items_iter.append(w)
                for it in items_iter:
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
                units_total = sum((c["quantity"] for c in cart_items), 0)
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
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", "")
    product = get_object_or_404(Product, id=product_id, is_active=True)
    size = (request.POST.get("size") or "").strip()
    color = (request.POST.get("color") or "").strip()
    variant = None
    if product.variants.exists():
        # Robust resolution: case/whitespace tolerant matching
        qs = product.variants.all()
        s = (size or "").strip()
        c = (color or "").strip()
        if s and c:
            variant = qs.filter(size__iexact=s, color__iexact=c).first()
            if not variant:
                # Fallback robust loop
                for v in qs:
                    vs = (getattr(v, "size", "") or "").strip().lower()
                    vc = (getattr(v, "color", "") or "").strip().lower()
                    if vs == s.lower() and vc == c.lower():
                        variant = v
                        break
        if not variant and s:
            variant = qs.filter(size__iexact=s).first()
        if not variant and c:
            variant = qs.filter(color__iexact=c).first()
        if not variant:
            variant = qs.first()

    qty = int(request.POST.get("quantity", 1))

    # Enforce stock availability for variants
    if variant:
        try:
            available = int(getattr(variant, "stock", 0) or 0)
            # Include any existing quantity of this variant in cart
            existing_qty = 0
            if request.user.is_authenticated:
                try:
                    cart_obj = _get_user_cart(request.user)
                    existing = cart_obj.items.filter(product=product, variant=variant).first()
                    existing_qty = existing.quantity if existing else 0
                except Exception:
                    existing_qty = 0
            else:
                # Check session cart
                try:
                    from .utils import _get_session_cart
                    sesi = _get_session_cart(request)
                    for it in sesi.get("items", []):
                        if it.get("product_id") == product.id and it.get("variant_id") == variant.id:
                            existing_qty = int(it.get("quantity", 0) or 0)
                            break
                except Exception:
                    existing_qty = 0
            desired_total = existing_qty + qty
            if desired_total > available:
                msg = "There are not enough items in stock."
                if is_ajax:
                    return JsonResponse({"ok": False, "error": "out_of_stock", "message": msg, "available": available}, status=400)
                messages.error(request, msg)
                # Redirect back to product page
                return redirect("product_detail", slug=product.slug)
        except Exception:
            pass
    # Buy Now flow: skip adding to cart, store as temporary session item
    if request.POST.get("buy_now") == "1":
        # Store selected variant info for reliable checkout summary
        # Compute unit price with variant-aware logic to persist for checkout
        try:
            unit_for_bn = (variant.price() if variant else product.price())
        except Exception:
            unit_for_bn = product.price()
        unit_for_bn = unit_for_bn.quantize(Decimal("0.01"))
        request.session["buy_now"] = {
            "product_id": product.id,
            "variant_id": (variant.id if variant else None),
            "size": size,
            "color": color,
            "quantity": qty,
            "unit_price": str(unit_for_bn),
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
    # Build quick response
    def _cart_count():
        try:
            if request.user.is_authenticated and hasattr(request.user, "cart"):
                return sum((it.quantity for it in request.user.cart.items.all()), 0)
            else:
                ses_items = get_session_items(request)
                return sum((it.quantity for it in ses_items), 0)
        except Exception:
            return 0

    if is_ajax:
        return JsonResponse({"ok": True, "message": "Added to cart", "cart_count": _cart_count()})
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
            # Stock check for variant
            var = getattr(item, "variant", None)
            if var and qty > int(getattr(var, "stock", 0) or 0):
                msg = "There are not enough items in stock."
                if is_ajax:
                    return JsonResponse({"ok": False, "error": "out_of_stock", "message": msg, "available": int(getattr(var, 'stock', 0) or 0)}, status=400)
                messages.error(request, msg)
                return redirect("view_cart")
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
            # Stock check for session item
            if vid:
                from catalog.models import Variant
                try:
                    vobj = Variant.objects.get(id=vid)
                    if qty > int(getattr(vobj, "stock", 0) or 0):
                        msg = "There are not enough items in stock."
                        if is_ajax:
                            return JsonResponse({"ok": False, "error": "out_of_stock", "message": msg, "available": int(getattr(vobj, 'stock', 0) or 0)}, status=400)
                        messages.error(request, msg)
                        return redirect("view_cart")
                except Variant.DoesNotExist:
                    pass
            update_session_item_session(request, pid, vid, qty)
            product = get_object_or_404(Product, id=pid)
            variant = Variant.objects.filter(id=vid).first() if vid else None
            unit = (variant.price() if variant else product.price())
            line_total = unit * qty
            resp.update({"pid": pid, "vid": vid, "item_total": str(line_total.quantize(Decimal("0.01")))})
    else:
        pid = int(request.POST.get("product_id"))
        vid_raw = request.POST.get("variant_id")
        vid = int(vid_raw) if vid_raw not in (None, "", "None") else None
        # For guest updates via session
        if vid:
            from catalog.models import Variant
            try:
                vobj = Variant.objects.get(id=vid)
                if qty > int(getattr(vobj, "stock", 0) or 0):
                    msg = "There are not enough items in stock."
                    if is_ajax:
                        return JsonResponse({"ok": False, "error": "out_of_stock", "message": msg, "available": int(getattr(vobj, 'stock', 0) or 0)}, status=400)
                    messages.error(request, msg)
                    return redirect("view_cart")
            except Variant.DoesNotExist:
                pass
        update_session_item_session(request, pid, vid, qty)
        product = get_object_or_404(Product, id=pid)
        variant = Variant.objects.filter(id=vid).first() if vid else None
        unit = (variant.price() if variant else product.price())
        line_total = unit * qty
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

    # Coupon application (mirror logic from view_cart)
    coupon_code = get_session_coupon(request)
    discount_amount = Decimal("0.00")
    if coupon_code:
        try:
            c = Coupon.objects.get(code__iexact=coupon_code)
            if c.is_valid():
                discount_amount = (subtotal * Decimal(c.discount_percent) / Decimal("100")).quantize(Decimal("0.01"))
        except Coupon.DoesNotExist:
            pass

    discounted_subtotal = (subtotal - discount_amount).quantize(Decimal("0.01"))
    if discounted_subtotal < 0:
        discounted_subtotal = Decimal("0.00")

    gst_amount = (discounted_subtotal * gst_rate).quantize(Decimal("0.01"))
    # Try dynamic estimate using session delivery pin or user's default address
    if discounted_subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
        shipping = Decimal("0.00")
    else:
        ship_estimate = None
        try:
            delivery = request.session.get("delivery") or {}
            drop_pin = (str(delivery.get("postal_code") or "").strip() or None)
            if not drop_pin and request.user.is_authenticated:
                addresses = Address.objects.filter(user=request.user)
                default_address = addresses.filter(is_default=True).first() or addresses.first()
                drop_pin = default_address.postal_code if default_address else None
            if drop_pin:
                total_w = Decimal("0.00")
                max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
                max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
                max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
                if request.user.is_authenticated and hasattr(request.user, "cart"):
                    items_iter = request.user.cart.items.select_related("product", "variant")
                else:
                    items_iter = get_session_items(request)
                units_total = 0
                for it in items_iter:
                    qty = getattr(it, 'quantity', 0) or 0
                    units_total += int(qty)
                    var = getattr(it, 'variant', None)
                    prod = getattr(it, 'product', None)
                    if var and getattr(var, "weight_kg", None):
                        w = Decimal(str(var.weight_kg))
                    elif prod and getattr(prod, "weight_kg", None):
                        w = Decimal(str(prod.weight_kg))
                    else:
                        w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
                    total_w += (w * Decimal(qty))
                    lv = (getattr(var, "length_cm", None) if var else None) or (getattr(prod, "length_cm", None) if prod else None)
                    bv = (getattr(var, "breadth_cm", None) if var else None) or (getattr(prod, "breadth_cm", None) if prod else None)
                    hv = (getattr(var, "height_cm", None) if var else None) or (getattr(prod, "height_cm", None) if prod else None)
                    if lv:
                        try: max_l = max(max_l, int(lv))
                        except Exception: pass
                    if bv:
                        try: max_b = max(max_b, int(bv))
                        except Exception: pass
                    if hv:
                        try: max_h = max(max_h, int(hv))
                        except Exception: pass
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
            shipping = Decimal(ship_estimate).quantize(Decimal("0.01"))
        else:
            shipping = flat
    total = (discounted_subtotal + gst_amount + shipping).quantize(Decimal("0.01"))

    resp.update({
        "subtotal": str(subtotal),
        "discount_amount": str(discount_amount),
        "discounted_subtotal": str(discounted_subtotal),
        "gst_amount": str(gst_amount),
        "shipping": str(shipping),
        "total": str(total),
        "cart_count": cart_count,
    })

    if is_ajax:
        return JsonResponse(resp)
    return redirect("view_cart")


def update_cart_variant(request, item_id):
    if request.method != "POST":
        return redirect("view_cart")
    size = request.POST.get("size")
    if not size:
        messages.error(request, "Select a size")
        return redirect("view_cart")
    # Auth path
    if request.user.is_authenticated:
        try:
            item = CartItem.objects.select_related("product", "variant", "cart").get(id=item_id, cart__user=request.user)
        except CartItem.DoesNotExist:
            messages.error(request, "Item not found")
            return redirect("view_cart")
        product = item.product
        cur_color = getattr(item.variant, "color", None)
        try:
            new_variant = product.variants.get(size=size, color=cur_color) if cur_color else product.variants.get(size=size)
        except Variant.DoesNotExist:
            messages.error(request, "Selected size not available")
            return redirect("view_cart")
        if item.variant_id == new_variant.id:
            return redirect("view_cart")
        # Merge if exists
        existing = CartItem.objects.filter(cart=item.cart, product=product, variant=new_variant).first()
        # Determine target quantity with clamp/reset-to-1 rule if new stock is lower than current qty
        try:
            new_stock = int(getattr(new_variant, "stock", 0) or 0)
        except Exception:
            new_stock = 0
        qty_current = int(getattr(item, "quantity", 1) or 1)
        # Clamp to new stock instead of resetting to 1
        qty_to_apply = max(1, min(qty_current, new_stock))
        if existing:
            # Merge and clamp to available stock
            if new_stock > 0:
                existing.quantity = min(int(existing.quantity) + qty_to_apply, new_stock)
            else:
                existing.quantity = int(existing.quantity) + qty_to_apply
            existing.save()
            # Remove original row
            item.delete()
        else:
            item.variant = new_variant
            item.quantity = qty_to_apply
            item.save(update_fields=["variant", "quantity"])
        messages.success(request, "Size updated")
        return redirect("view_cart")
    # Session path
    try:
        pid = int(request.POST.get("product_id"))
    except Exception:
        return redirect("view_cart")
    product = get_object_or_404(Product, id=pid)
    vid_raw = request.POST.get("variant_id")
    cur_vid = int(vid_raw) if vid_raw not in (None, "", "None") else None
    cur_variant = Variant.objects.filter(id=cur_vid).first() if cur_vid else None
    cur_color = getattr(cur_variant, "color", None)
    try:
        new_variant = product.variants.get(size=size, color=cur_color) if cur_color else product.variants.get(size=size)
    except Variant.DoesNotExist:
        messages.error(request, "Selected size not available")
        return redirect("view_cart")
    # Determine current qty in session and clamp/reset when switching to a lower-stock variant
    ses_items = get_session_items(request)
    qty = 1
    for it in ses_items:
        if it.product.id == pid and ((it.variant and it.variant.id) == cur_vid or (it.variant is None and cur_vid is None)):
            qty = it.quantity
            break
    try:
        new_stock = int(getattr(new_variant, "stock", 0) or 0)
    except Exception:
        new_stock = 0
    # Clamp to new stock instead of resetting to 1
    qty_to_apply = max(1, min(qty, new_stock))
    remove_session_item_session(request, pid, cur_vid)
    add_session_item(request, pid, new_variant.id if new_variant else None, qty_to_apply)
    messages.success(request, "Size updated")
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
    # Coupon + discounted subtotal
    coupon_code = get_session_coupon(request)
    discount_amount = Decimal("0.00")
    if coupon_code:
        try:
            c = Coupon.objects.get(code__iexact=coupon_code)
            if c.is_valid():
                discount_amount = (subtotal * Decimal(c.discount_percent) / Decimal("100")).quantize(Decimal("0.01"))
        except Coupon.DoesNotExist:
            pass
    discounted_subtotal = (subtotal - discount_amount).quantize(Decimal("0.01"))
    if discounted_subtotal < 0:
        discounted_subtotal = Decimal("0.00")
    gst_amount = (discounted_subtotal * gst_rate).quantize(Decimal("0.01"))
    # Dynamic estimate using session delivery pin or default address
    if discounted_subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
        shipping = Decimal("0.00")
    else:
        ship_estimate = None
        try:
            delivery = request.session.get("delivery") or {}
            drop_pin = (str(delivery.get("postal_code") or "").strip() or None)
            if not drop_pin and request.user.is_authenticated and hasattr(request.user, "cart"):
                addresses = Address.objects.filter(user=request.user)
                default_address = addresses.filter(is_default=True).first() or addresses.first()
                drop_pin = default_address.postal_code if default_address else None
            if drop_pin:
                total_w = Decimal("0.00")
                max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
                max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
                max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
                items_iter = None
                if request.user.is_authenticated and hasattr(request.user, "cart"):
                    items_iter = request.user.cart.items.select_related("product", "variant")
                else:
                    items_iter = get_session_items(request)
                units_total = 0
                for it in items_iter:
                    qty = getattr(it, 'quantity', 0) or 0
                    units_total += int(qty)
                    var = getattr(it, 'variant', None)
                    prod = getattr(it, 'product', None)
                    if var and getattr(var, "weight_kg", None):
                        w = Decimal(str(var.weight_kg))
                    elif prod and getattr(prod, "weight_kg", None):
                        w = Decimal(str(prod.weight_kg))
                    else:
                        w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
                    total_w += (w * Decimal(qty))
                    lv = (getattr(var, "length_cm", None) if var else None) or (getattr(prod, "length_cm", None) if prod else None)
                    bv = (getattr(var, "breadth_cm", None) if var else None) or (getattr(prod, "breadth_cm", None) if prod else None)
                    hv = (getattr(var, "height_cm", None) if var else None) or (getattr(prod, "height_cm", None) if prod else None)
                    if lv:
                        try: max_l = max(max_l, int(lv))
                        except Exception: pass
                    if bv:
                        try: max_b = max(max_b, int(bv))
                        except Exception: pass
                    if hv:
                        try: max_h = max(max_h, int(hv))
                        except Exception: pass
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
        shipping = ship_estimate.quantize(Decimal("0.01")) if ship_estimate is not None else flat
    total = (discounted_subtotal + gst_amount + shipping).quantize(Decimal("0.01"))

    if is_ajax:
        return JsonResponse({
            "ok": True,
            "pid": pid,
            "vid": vid,
            "subtotal": str(subtotal),
            "discount_amount": str(discount_amount),
            "discounted_subtotal": str(discounted_subtotal),
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
