import uuid
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.conf import settings
from cart.models import Cart
from .models import Order, OrderItem
from payments.utils import create_razorpay_order
from .shiprocket import estimate_shipping_charge
from cart.utils import get_session_items, clear_session_cart, get_session_coupon, clear_session_coupon
from coupons.models import Coupon
from accounts.models import Address
from .shiprocket import create_shiprocket_return
from .models import ReturnRequest, ReturnItem
from catalog.models import Variant


def _generate_order_number() -> str:
    return uuid.uuid4().hex[:10].upper()


@login_required
def checkout(request):
    # Detect Buy Now mode (single-item checkout)
    buy_now_data = request.session.get("buy_now")
    buy_now_mode = bool(buy_now_data)
    # Allow explicit override via query param when coming from cart
    override_bn = (request.GET.get("bn") or "").lower()
    if override_bn in ("0", "false", "cart"):
        buy_now_mode = False
        try:
            request.session.pop("buy_now")
        except Exception:
            pass

    # Merge any session cart items into the user's cart on first checkout
    # Skip when in Buy Now mode so we don't pollute the user's cart
    if not buy_now_mode:
        ses_items = get_session_items(request)
        if ses_items:
            cart = getattr(request.user, "cart", None)
            if not cart:
                cart = Cart.objects.create(user=request.user)
            for it in ses_items:
                db_item, created = cart.items.get_or_create(product=it.product, variant=it.variant, defaults={"quantity": it.quantity})
                if not created:
                    db_item.quantity += it.quantity
                    db_item.save()
            clear_session_cart(request)

    cart = getattr(request.user, "cart", None)
    if not buy_now_mode and (not cart or cart.items.count() == 0):
        messages.error(request, "Your cart is empty")
        return redirect("view_cart")

    # Subtotal: for Buy Now use only the selected item; else use cart
    if buy_now_mode:
        from catalog.models import Product
        try:
            bn_product = Product.objects.get(id=int(buy_now_data.get("product_id")))
        except Exception:
            messages.error(request, "Selected item is unavailable.")
            return redirect("/")
        bn_variant = None
        v_id = buy_now_data.get("variant_id")
        if v_id not in (None, "", "None"):
            try:
                bn_variant = Variant.objects.get(id=int(v_id))
            except Exception:
                bn_variant = None
        bn_qty = max(1, int(buy_now_data.get("quantity", 1)))
        subtotal = (bn_product.price() * bn_qty).quantize(Decimal("0.01"))
    else:
        subtotal = cart.subtotal()
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

    # Estimate shipment charge using default address when available; fallback to flat
    addresses = Address.objects.filter(user=request.user)
    selected_id = request.GET.get("address_id")
    default_address = None
    if selected_id:
        try:
            default_address = addresses.get(id=int(selected_id))
        except (Address.DoesNotExist, ValueError, TypeError):
            default_address = None
    if not default_address:
        default_address = addresses.filter(is_default=True).first() or addresses.first()

    # Helpers for weight/dimensions based on product/variant fields
    def _items_total_weight_dims():
        total_w = Decimal("0.00")
        max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
        max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
        max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
        if buy_now_mode:
            sources = [(bn_product, bn_variant, bn_qty)]
        else:
            sources = [(it.product, it.variant, it.quantity) for it in cart.items.select_related("product", "variant")]
        for prod, var, qty in sources:
            if var and getattr(var, "weight_kg", None):
                w = Decimal(str(var.weight_kg))
            elif getattr(prod, "weight_kg", None):
                w = Decimal(str(prod.weight_kg))
            else:
                w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
            total_w += (w * Decimal(qty))
            lv = (getattr(var, "length_cm", None) if var else None) or getattr(prod, "length_cm", None)
            bv = (getattr(var, "breadth_cm", None) if var else None) or getattr(prod, "breadth_cm", None)
            hv = (getattr(var, "height_cm", None) if var else None) or getattr(prod, "height_cm", None)
            if lv:
                try: max_l = max(max_l, int(lv))
                except Exception: pass
            if bv:
                try: max_b = max(max_b, int(bv))
                except Exception: pass
            if hv:
                try: max_h = max(max_h, int(hv))
                except Exception: pass
        return total_w, (max_l, max_b, max_h)

    # Free shipping threshold still applies
    shipping = Decimal("0.00")
    if discounted_subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
        shipping = Decimal("0.00")
    else:
        # Try Shiprocket estimate when configured and address present
        ship_estimate = None
        try:
            if buy_now_mode:
                units_total = bn_qty
            else:
                cart = getattr(request.user, "cart", None)
                units_total = sum((it.quantity for it in cart.items.all()), 0) if cart else 0
            drop_pin = default_address.postal_code if default_address else None
            if drop_pin:
                total_w, dims = _items_total_weight_dims()
                ship_est = estimate_shipping_charge(
                    drop_pin=str(drop_pin),
                    units_total=units_total or 1,
                    cod=False,
                    declared_value=discounted_subtotal,
                    total_weight_kg=total_w,
                    dims_cm=dims,
                )
                ship_estimate = ship_est
        except Exception:
            ship_estimate = None

        if ship_estimate is not None:
            shipping = ship_estimate.quantize(Decimal("0.01"))
        else:
            flat = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))
            shipping = flat

    total = (discounted_subtotal + gst_amount + shipping).quantize(Decimal("0.01"))

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")
        if payment_method not in ("razorpay", "cod"):
            messages.error(request, "Select a valid payment method")
            return redirect("checkout")

        order_number = _generate_order_number()
        # Use selected saved address if provided
        addr_id = request.POST.get("address_id")
        addr_obj = None
        if addr_id:
            try:
                addr_obj = Address.objects.get(user=request.user, id=int(addr_id))
            except (Address.DoesNotExist, ValueError, TypeError):
                addr_obj = None

        # Compute shipment charge using selected address and payment method
        shipping_for_order = Decimal("0.00")
        if discounted_subtotal >= Decimal(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)):
            shipping_for_order = Decimal("0.00")
        else:
            try:
                if buy_now_mode:
                    units_total = bn_qty
                else:
                    cart_for_units = getattr(request.user, "cart", None)
                    units_total = sum((it.quantity for it in cart_for_units.items.all()), 0) if cart_for_units else 1
                drop_pin = (addr_obj.postal_code if addr_obj else request.POST.get("postal_code")) or ""
                est = None
                if drop_pin:
                    total_w, dims = _items_total_weight_dims()
                    est = estimate_shipping_charge(
                        drop_pin=str(drop_pin),
                        units_total=units_total or 1,
                        cod=(payment_method == "cod"),
                        declared_value=discounted_subtotal,
                        total_weight_kg=total_w,
                        dims_cm=dims,
                    )
                if est is not None:
                    shipping_for_order = est.quantize(Decimal("0.01"))
                else:
                    shipping_for_order = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))
            except Exception:
                shipping_for_order = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))

        total = (discounted_subtotal + gst_amount + shipping_for_order).quantize(Decimal("0.01"))

        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            status="created",
            payment_method=payment_method,
            subtotal=discounted_subtotal,
            discount_amount=discount_amount,
            coupon_code=coupon.code if coupon else "",
            gst_amount=gst_amount,
            shipping_amount=shipping_for_order,
            total_amount=total,
            shipping_name=(addr_obj.full_name if addr_obj else (request.POST.get("shipping_name") or request.user.get_full_name() or request.user.username)),
            shipping_phone=(addr_obj.phone if addr_obj else request.POST.get("shipping_phone", "")),
            address_line1=(addr_obj.address_line1 if addr_obj else request.POST.get("address_line1", "")),
            address_line2=(addr_obj.address_line2 if addr_obj else request.POST.get("address_line2", "")),
            city=(addr_obj.city if addr_obj else request.POST.get("city", "")),
            state=(addr_obj.state if addr_obj else request.POST.get("state", "")),
            postal_code=(addr_obj.postal_code if addr_obj else request.POST.get("postal_code", "")),
            country=(addr_obj.country if addr_obj else "India"),
        )

        if buy_now_mode:
            unit_cost_val = Decimal("0.00")
            if bn_variant and getattr(bn_variant, "cost_price", None) is not None:
                try:
                    unit_cost_val = Decimal(str(bn_variant.cost_price))
                except Exception:
                    unit_cost_val = Decimal("0.00")
            OrderItem.objects.create(
                order=order,
                product=bn_product,
                variant=bn_variant,
                quantity=bn_qty,
                unit_price=bn_product.price(),
                line_total=(bn_product.price() * bn_qty).quantize(Decimal("0.01")),
                unit_cost=unit_cost_val,
                line_cost=(unit_cost_val * Decimal(bn_qty)).quantize(Decimal("0.01")),
            )
        else:
            for item in cart.items.select_related("product", "variant"):
                # Resolve unit cost from variant/product cost_price if available
                unit_cost_val = Decimal("0.00")
                if item.variant and getattr(item.variant, "cost_price", None) is not None:
                    try:
                        unit_cost_val = Decimal(str(item.variant.cost_price))
                    except Exception:
                        unit_cost_val = Decimal("0.00")
                # Fallback: product doesn't yet have cost_price field; leave 0
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                    unit_price=item.unit_price(),
                    line_total=item.line_total(),
                    unit_cost=unit_cost_val,
                    line_cost=(unit_cost_val * Decimal(item.quantity)).quantize(Decimal("0.01")),
                )

        if payment_method == "razorpay":
            rp_order = create_razorpay_order(int(total * 100), receipt=order_number)
            order.razorpay_order_id = rp_order.get("id", "")
            order.save()
            # Clear temp buy-now item
            if buy_now_mode:
                try:
                    request.session.pop("buy_now")
                except Exception:
                    pass
            return render(
                request,
                "orders/razorpay_pay.html",
                {
                    "order": order,
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                    "amount_paise": int(total * 100),
                    "currency": "INR",
                },
            )
        else:  # COD
            order.status = "created"
            order.save()
            if not buy_now_mode and cart:
                cart.items.all().delete()
            clear_session_coupon(request)
            if buy_now_mode:
                try:
                    request.session.pop("buy_now")
                except Exception:
                    pass
            messages.success(request, f"COD order placed: {order.order_number}")
            return redirect("order_detail", order_number=order.order_number)

    return render(
        request,
        "orders/checkout.html",
        {
            "cart": cart,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "discounted_subtotal": discounted_subtotal,
            "coupon_code": coupon_code,
            "gst_amount": gst_amount,
            "shipping": shipping,
            "total": total,
            "addresses": addresses,
            "default_address": default_address,
        },
    )


@login_required
def order_list(request):
    orders = (
        Order.objects.filter(user=request.user)
        .order_by("-created_at")
        .prefetch_related("items__product__images")
    )
    return render(request, "orders/order_list.html", {"orders": orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(Order, user=request.user, order_number=order_number)
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def order_support(request, order_number):
    order = get_object_or_404(Order, user=request.user, order_number=order_number)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "not_received":
            _ = (request.POST.get("details") or "").strip()
            messages.info(request, "Thanks. We've recorded that you haven't received this order. Our team will review and reach out.")
            return redirect("order_support", order_number=order.order_number)
        if action == "delivery_feedback":
            _ = (request.POST.get("feedback") or "").strip()
            messages.success(request, "Thanks for your feedback on the delivery associate.")
            return redirect("order_support", order_number=order.order_number)
    return render(request, "orders/order_support.html", {"order": order})


@login_required
def order_invoice(request, order_number):
    order = get_object_or_404(Order, user=request.user, order_number=order_number)
    return render(request, "orders/invoice.html", {"order": order})


@login_required
def order_track(request, order_number):
    order = get_object_or_404(Order, user=request.user, order_number=order_number)
    tracking = None
    if order.tracking_number:
        tracking = track_awb(order.tracking_number)
    return render(request, "orders/track.html", {"order": order, "tracking": tracking})


@login_required
def order_return_request(request, order_number):
    order = get_object_or_404(Order, user=request.user, order_number=order_number)
    if request.method == "POST":
        rtype = request.POST.get("type", "return")
        reason = request.POST.get("reason", "")
        sel_items = []
        for it in order.items.select_related("product", "variant"):
            qty = int(request.POST.get(f"qty_{it.id}", 0) or 0)
            if qty > 0:
                # Clamp to max allowed
                qty = min(qty, it.quantity)
                # Exchange variant optional when type is exchange
                ex_var = None
                if rtype == "exchange":
                    ex_id = request.POST.get(f"ex_{it.id}_variant")
                    if ex_id:
                        try:
                            ex_var = Variant.objects.get(id=int(ex_id))
                        except (Variant.DoesNotExist, ValueError, TypeError):
                            ex_var = None
                sel_items.append((it, qty, ex_var))
        if not sel_items:
            messages.error(request, "Select at least one item to return/exchange")
            return redirect("order_return_request", order_number=order_number)
        rr = ReturnRequest.objects.create(order=order, user=request.user, type=rtype, reason=reason, status="requested")
        for it, qty, ex_var in sel_items:
            ReturnItem.objects.create(request=rr, order_item=it, quantity=qty, exchange_variant=ex_var)
        # Try creating Shiprocket reverse pickup immediately
        try:
            items = []
            for it, qty, _ in sel_items:
                fake = it
                fake.quantity = qty
                items.append(fake)
            awb = create_shiprocket_return(order, items)
            if awb:
                rr.awb_code = awb
                rr.status = "pickup_scheduled"
                rr.save()
                # Update order status
                order.status = "return_requested" if rtype == "return" else "exchange_requested"
                order.save(update_fields=["status", "updated_at"])
                messages.success(request, f"{rtype.title()} initiated. AWB: {awb}")
            else:
                messages.info(request, "Request recorded. We'll schedule a pickup soon.")
        except Exception:
            messages.info(request, "Request recorded. We'll schedule a pickup soon.")
        return redirect("order_detail", order_number=order.order_number)
    return render(request, "orders/return_request.html", {"order": order})


@login_required
def order_return_quick(request, order_number):
    """Initiate a full-order return via Shiprocket (reverse pickup) in one click.
    Creates a ReturnRequest for all items with full quantities.
    Visible only for delivered orders.
    """
    order = get_object_or_404(Order, user=request.user, order_number=order_number)
    if order.status != "delivered":
        messages.error(request, "You can request a return after the order is delivered.")
        return redirect("order_detail", order_number=order_number)
    rr = ReturnRequest.objects.create(order=order, user=request.user, type="return", reason="Quick return", status="requested")
    selected_items = []
    for it in order.items.select_related("product", "variant"):
        ReturnItem.objects.create(request=rr, order_item=it, quantity=it.quantity)
        # prepare copy for Shiprocket return call
        fake = it
        fake.quantity = it.quantity
        selected_items.append(fake)
    try:
        awb = create_shiprocket_return(order, selected_items)
        if awb:
            rr.awb_code = awb
            rr.status = "pickup_scheduled"
            rr.save()
            order.status = "return_requested"
            order.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Return initiated. AWB: {awb}")
        else:
            messages.info(request, "Return request recorded. We'll schedule a pickup soon.")
    except Exception:
        messages.info(request, "Return request recorded. We'll schedule a pickup soon.")
    return redirect("order_detail", order_number=order.order_number)
