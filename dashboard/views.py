from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, F
from django.db.models.functions import TruncDate, TruncMonth
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
import json
from django.utils import timezone
from decimal import Decimal
import random
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.core.mail import send_mail, EmailMessage, get_connection
import logging
logger = logging.getLogger(__name__)

from orders.models import Order, OrderItem
from catalog.models import Variant, Product, Category, ProductImage, ProductVideo
from core.models import Banner
from coupons.models import Coupon
from django.contrib.auth import get_user_model
from .forms import (
    CategoryForm,
    ProductForm,
    BannerForm,
    OrderForm,
    OrderItemForm,
    ProductImageForm,
    ProductVideoForm,
    VariantForm,
)


@staff_member_required(login_url="/accounts/login/")
def index(request):
    orders_paid = Order.objects.filter(status__in=["paid", "shipped", "delivered"]) \
        .aggregate(total=Sum("total_amount"))
    revenue = orders_paid["total"] or 0

    latest_orders = Order.objects.select_related("user").order_by("-created_at")[:10]

    stock_summary = Variant.objects.aggregate(total_qty=Sum("stock"))

    return render(request, "dashboard/index.html", {
        "revenue": revenue,
        "latest_orders": latest_orders,
        "stock_total": stock_summary["total_qty"] or 0,
        "orders_count": Order.objects.count(),
    })


@staff_member_required(login_url="/accounts/login/")
def analytics_data(request):
    from django.conf import settings
    try:
        days = int(request.GET.get("days", "30"))
    except Exception:
        days = 30
    days = max(1, min(days, 365))
    group = request.GET.get("group", "day")
    from django.utils import timezone
    start = timezone.now() - timezone.timedelta(days=days-1)

    revenue_statuses = ["paid", "shipped", "delivered"]

    trunc = TruncDate
    if group == "month":
        trunc = TruncMonth

    qs = (
        Order.objects.filter(created_at__date__gte=start.date(), status__in=revenue_statuses)
        .annotate(d=trunc("created_at"))
        .values("d")
        .annotate(
            revenue=Sum("total_amount"),
            subtotal=Sum("subtotal"),
            tax=Sum("gst_amount"),
            shipping=Sum("shipping_amount"),
            discount=Sum("discount_amount"),
            # Real cost from items (if captured), else 0
            real_cost=Sum("items__line_cost"),
        )
        .order_by("d")
    )

    # Build complete timeline with zeros for missing days/months so chart always renders
    from django.utils import timezone as dj_tz
    cogs_rate = float(getattr(settings, "COGS_RATE", 0.0) or 0.0)
    agg = {}
    for row in qs:
        key = row["d"].strftime("%Y-%m" if group == "month" else "%Y-%m-%d")
        agg[key] = row

    labels, revenue, net_sales, profit = [], [], [], []
    cursor = start
    today = dj_tz.now()
    while (cursor.year, cursor.month, cursor.day) <= (today.year, today.month, today.day):
        key = cursor.strftime("%Y-%m" if group == "month" else "%Y-%m-%d")
        row = agg.get(key, {})
        rev = float(row.get("revenue") or 0)
        sub = float(row.get("subtotal") or 0)
        disc = float(row.get("discount") or 0)
        ship = float(row.get("shipping") or 0)
        real_cost = float(row.get("real_cost") or 0)
        net = max(sub - disc, 0.0)
        est_profit = (net - real_cost - ship) if real_cost > 0 else (net * (1.0 - cogs_rate) - ship)
        labels.append(key)
        revenue.append(round(rev, 2))
        net_sales.append(round(net, 2))
        profit.append(round(est_profit, 2))
        if group == "month":
            # advance to first day of next month
            y = cursor.year + (1 if cursor.month == 12 else 0)
            m = 1 if cursor.month == 12 else cursor.month + 1
            cursor = cursor.replace(year=y, month=m, day=1)
        else:
            cursor += dj_tz.timedelta(days=1)

    return JsonResponse({
        "labels": labels,
        "datasets": {
            "revenue": revenue,
            "net_sales": net_sales,
            "profit": profit,
        },
        "meta": {"cogs_rate": cogs_rate, "group": group, "days": days},
    })


@staff_member_required(login_url="/accounts/login/")
def analytics_csv(request):
    from django.conf import settings
    import csv
    from django.http import HttpResponse
    try:
        days = int(request.GET.get("days", "30"))
    except Exception:
        days = 30
    days = max(1, min(days, 365))
    group = request.GET.get("group", "day")

    # Build same data as JSON
    from django.utils import timezone
    start = timezone.now() - timezone.timedelta(days=days-1)
    revenue_statuses = ["paid", "shipped", "delivered"]
    trunc = TruncMonth if group == "month" else TruncDate
    qs = (
        Order.objects.filter(created_at__date__gte=start.date(), status__in=revenue_statuses)
        .annotate(d=trunc("created_at"))
        .values("d")
        .annotate(
            revenue=Sum("total_amount"),
            subtotal=Sum("subtotal"),
            tax=Sum("gst_amount"),
            shipping=Sum("shipping_amount"),
            discount=Sum("discount_amount"),
        )
        .order_by("d")
    )
    cogs_rate = float(getattr(settings, "COGS_RATE", 0.0) or 0.0)

    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="analytics.csv"'
    w = csv.writer(resp)
    w.writerow(["date", "revenue", "net_sales", "estimated_profit"]) 
    for row in qs:
        if group == "month":
            d = row["d"].strftime("%Y-%m")
        else:
            d = row["d"].strftime("%Y-%m-%d")
        sub = float(row.get("subtotal") or 0)
        disc = float(row.get("discount") or 0)
        ship = float(row.get("shipping") or 0)
        net = max(sub - disc, 0.0)
        est_profit = net * (1.0 - cogs_rate) - ship
        w.writerow([
            d,
            round(float(row.get("revenue") or 0), 2),
            round(net, 2),
            round(est_profit, 2),
        ])
    return resp


@staff_member_required(login_url="/accounts/login/")
def orders_list(request):
    q = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "all")
    selected_sort = request.GET.get("sort", "newest")

    qs = Order.objects.all()
    if q:
        qs = qs.filter(order_number__icontains=q) | qs.filter(user__username__icontains=q)
    if selected_status and selected_status != "all":
        qs = qs.filter(status=selected_status)

    if selected_sort == "oldest":
        qs = qs.order_by("created_at")
    else:
        qs = qs.order_by("-created_at")
    orders = (
        qs.select_related("user").prefetch_related("items__product__images", "items__variant")
    )[:50]
    # Enrich with first item thumb + size/color
    for o in orders:
        try:
            it = o.items.select_related("product", "variant").first()
            if not it:
                o.thumb_url = ""; o.first_size = ""; o.first_color = ""; o.first_item_name = ""; o.item_thumbs = []; o.item_more_count = 0; continue
            size = (getattr(it.variant, "size", None) or it.variant_size or "")
            color = (getattr(it.variant, "color", None) or it.variant_color or "")
            thumb = ""
            imgs = list(getattr(it.product, "images", None).all()) if getattr(it.product, "images", None) else []
            if color:
                low = str(color).strip().lower()
                for im in imgs:
                    c = (getattr(im, "color", "") or "").strip().lower()
                    if c and c == low and getattr(im, "image", None) and getattr(im.image, "url", None):
                        thumb = im.image.url; break
            if not thumb and imgs:
                first = imgs[0]
                if getattr(first, "image", None) and getattr(first.image, "url", None):
                    thumb = first.image.url
            o.thumb_url = thumb
            o.first_size = size
            o.first_color = color
            o.first_item_name = it.product.name
            # Build up to 3 additional item thumbnails across order items (exclude first item's thumb)
            thumbs = []
            for item in o.items.select_related("product", "variant").all():
                t = ""
                try:
                    imlist = list(getattr(item.product, "images", None).all()) if getattr(item.product, "images", None) else []
                    icol = (getattr(item.variant, "color", None) or item.variant_color or "")
                    if icol:
                        lowc = str(icol).strip().lower()
                        for im in imlist:
                            cc = (getattr(im, "color", "") or "").strip().lower()
                            if cc and cc == lowc and getattr(im, "image", None) and getattr(im.image, "url", None):
                                t = im.image.url; break
                    if not t and imlist:
                        fi = imlist[0]
                        if getattr(fi, "image", None) and getattr(fi.image, "url", None):
                            t = fi.image.url
                except Exception:
                    t = ""
                if t and t != thumb and t not in thumbs:
                    thumbs.append(t)
                if len(thumbs) >= 3:
                    break
            o.item_thumbs = thumbs
            o.item_more_count = max(0, o.items.count() - 1 - len(thumbs))
        except Exception:
            o.thumb_url = ""; o.first_size = ""; o.first_color = ""; o.first_item_name = ""; o.item_thumbs = []; o.item_more_count = 0

    summary = qs.aggregate(total_amount=Sum("total_amount"))
    total_amount = summary.get("total_amount") or 0
    total_orders = qs.count()

    return render(
        request,
        "dashboard/orders_list.html",
        {
            "orders": orders,
            "status_choices": Order.STATUS_CHOICES,
            "selected_status": selected_status,
            "selected_sort": selected_sort,
            "q": q,
            "summary_total_amount": total_amount,
            "summary_total_orders": total_orders,
        },
    )


@staff_member_required(login_url="/accounts/login/")
def orders_partial(request):
    q = request.GET.get("q", "").strip()
    selected_status = request.GET.get("status", "all")
    selected_sort = request.GET.get("sort", "newest")

    qs = Order.objects.all()
    if q:
        qs = qs.filter(order_number__icontains=q) | qs.filter(user__username__icontains=q)
    if selected_status and selected_status != "all":
        qs = qs.filter(status=selected_status)
    if selected_sort == "oldest":
        qs = qs.order_by("created_at")
    else:
        qs = qs.order_by("-created_at")

    orders = (
        qs.select_related("user").prefetch_related("items__product__images", "items__variant")
    )[:50]
    for o in orders:
        try:
            it = o.items.select_related("product", "variant").first()
            if not it:
                o.thumb_url = ""; o.first_size = ""; o.first_color = ""; o.first_item_name = ""; o.item_thumbs = []; o.item_more_count = 0; continue
            size = (getattr(it.variant, "size", None) or it.variant_size or "")
            color = (getattr(it.variant, "color", None) or it.variant_color or "")
            thumb = ""
            imgs = list(getattr(it.product, "images", None).all()) if getattr(it.product, "images", None) else []
            if color:
                low = str(color).strip().lower()
                for im in imgs:
                    c = (getattr(im, "color", "") or "").strip().lower()
                    if c and c == low and getattr(im, "image", None) and getattr(im.image, "url", None):
                        thumb = im.image.url; break
            if not thumb and imgs:
                first = imgs[0]
                if getattr(first, "image", None) and getattr(first.image, "url", None):
                    thumb = first.image.url
            o.thumb_url = thumb
            o.first_size = size
            o.first_color = color
            o.first_item_name = it.product.name
            thumbs = []
            for item in o.items.select_related("product", "variant").all():
                t = ""
                try:
                    imlist = list(getattr(item.product, "images", None).all()) if getattr(item.product, "images", None) else []
                    icol = (getattr(item.variant, "color", None) or item.variant_color or "")
                    if icol:
                        lowc = str(icol).strip().lower()
                        for im in imlist:
                            cc = (getattr(im, "color", "") or "").strip().lower()
                            if cc and cc == lowc and getattr(im, "image", None) and getattr(im.image, "url", None):
                                t = im.image.url; break
                    if not t and imlist:
                        fi = imlist[0]
                        if getattr(fi, "image", None) and getattr(fi.image, "url", None):
                            t = fi.image.url
                except Exception:
                    t = ""
                if t and t != thumb and t not in thumbs:
                    thumbs.append(t)
                if len(thumbs) >= 3:
                    break
            o.item_thumbs = thumbs
            o.item_more_count = max(0, o.items.count() - 1 - len(thumbs))
        except Exception:
            o.thumb_url = ""; o.first_size = ""; o.first_color = ""; o.first_item_name = ""; o.item_thumbs = []; o.item_more_count = 0
    summary = qs.aggregate(total_amount=Sum("total_amount"))
    total_amount = summary.get("total_amount") or 0
    total_orders = qs.count()

    rows_html = render_to_string(
        "dashboard/_orders_rows.html",
        {"orders": orders, "status_choices": Order.STATUS_CHOICES},
        request=request,
    )
    summary_html = render_to_string(
        "dashboard/_orders_summary.html",
        {"summary_total_orders": total_orders, "summary_total_amount": total_amount},
        request=request,
    )
    return JsonResponse({"rows_html": rows_html, "summary_html": summary_html})


@staff_member_required(login_url="/accounts/login/")
def order_detail_admin(request, pk: int):
    order = get_object_or_404(
        Order.objects.select_related("user").prefetch_related("items__product__images", "items__variant"),
        pk=pk,
    )
    # Build color-aware thumbnails and expose size/color for each item
    items = []
    for it in order.items.select_related("product", "variant").all():
        size = (getattr(it.variant, "size", None) or it.variant_size or "")
        color = (getattr(it.variant, "color", None) or it.variant_color or "")
        img_url = ""
        try:
            imgs = list(getattr(it.product, "images", None).all()) if getattr(it.product, "images", None) else []
            if color:
                low = str(color).strip().lower()
                for im in imgs:
                    c = (getattr(im, "color", "") or "").strip().lower()
                    if c and c == low and getattr(im, "image", None) and getattr(im.image, "url", None):
                        img_url = im.image.url
                        break
            if not img_url and imgs:
                first = imgs[0]
                if getattr(first, "image", None) and getattr(first.image, "url", None):
                    img_url = first.image.url
        except Exception:
            img_url = ""
        items.append({
            "product": it.product,
            "variant": it.variant,
            "size": size,
            "color": color,
            "qty": it.quantity,
            "unit_price": it.unit_price,
            "line_total": it.line_total,
            "img_url": img_url,
        })
    return render(request, "dashboard/order_detail.html", {"order": order, "items": items})


@staff_member_required(login_url="/accounts/login/")
def products_list(request):
    q = request.GET.get("q", "").strip()
    qs = Product.objects.select_related("category").all()
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(category__name__icontains=q)
    products = qs.order_by("-created_at")[:100]
    return render(request, "dashboard/products_list.html", {"products": products, "q": q})


@staff_member_required(login_url="/accounts/login/")
def categories_list(request):
    q = request.GET.get("q", "").strip()
    qs = Category.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    categories = qs.order_by("name")
    return render(request, "dashboard/categories_list.html", {"categories": categories, "q": q})


@staff_member_required(login_url="/accounts/login/")
def banners_list(request):
    q = request.GET.get("q", "").strip()
    qs = Banner.objects.all()
    if q:
        qs = qs.filter(title__icontains=q)
    banners = qs.order_by("sort_order", "-created_at")
    return render(request, "dashboard/banners_list.html", {"banners": banners, "q": q})


@staff_member_required(login_url="/accounts/login/")
def create_category(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Category created")
            return redirect("dashboard")
    else:
        form = CategoryForm()
    return render(request, "dashboard/category_form.html", {"form": form})


@staff_member_required(login_url="/accounts/login/")
def create_product(request):
    ImageFormSet = inlineformset_factory(Product, ProductImage, form=ProductImageForm, extra=1, can_delete=True)
    VideoFormSet = inlineformset_factory(Product, ProductVideo, form=ProductVideoForm, extra=1, can_delete=True)
    VariantFormSet = inlineformset_factory(Product, Variant, form=VariantForm, extra=1, can_delete=True)

    if request.method == "POST":
        form = ProductForm(request.POST)
        # Bind inline formsets to an unsaved instance for validation
        product_candidate = form.instance  # unsaved Product from ModelForm
        images_fs = ImageFormSet(request.POST, request.FILES, instance=product_candidate, prefix="images")
        videos_fs = VideoFormSet(request.POST, request.FILES, instance=product_candidate, prefix="videos")
        variants_fs = VariantFormSet(request.POST, instance=product_candidate, prefix="variants")
        # Build variant colors from submitted variant forms for suggestions
        var_colors = []
        try:
            for k, v in request.POST.items():
                if k.startswith('variants-') and k.endswith('-color') and v.strip():
                    if v not in var_colors:
                        var_colors.append(v)
        except Exception:
            var_colors = []
        if form.is_valid() and images_fs.is_valid() and videos_fs.is_valid() and variants_fs.is_valid():
            from django.db import transaction, IntegrityError
            try:
                with transaction.atomic():
                    product = form.save()
                    images_fs.instance = product
                    videos_fs.instance = product
                    variants_fs.instance = product
                    images_fs.save()
                    videos_fs.save()
                    variants_fs.save()
                messages.success(request, "Product created")
                return redirect("dashboard_products")
            except IntegrityError:
                form.add_error(None, "Could not save product due to a conflict (duplicate slug/SKU). Please adjust name or SKUs.")
    else:
        form = ProductForm()
        blank_product = Product()
        images_fs = ImageFormSet(instance=blank_product, prefix="images")
        videos_fs = VideoFormSet(instance=blank_product, prefix="videos")
        variants_fs = VariantFormSet(instance=blank_product, prefix="variants")
        # Default colors from Variant choices for suggestions
        try:
            from catalog.models import Variant as _Variant
            var_colors = [c for c in {c for c in dict(_Variant.COLOR_CHOICES).keys()}]
        except Exception:
            var_colors = ["Red", "Black", "Navy Blue", "White", "Grey"]
    return render(request, "dashboard/product_form.html", {
        "form": form,
        "images_fs": images_fs,
        "videos_fs": videos_fs,
        "variants_fs": variants_fs,
        "form_title": "Create Product",
        "submit_label": "Create Product",
        "variant_colors": var_colors,
    })


@staff_member_required(login_url="/accounts/login/")
def create_banner(request):
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Banner created")
            return redirect("dashboard")
    else:
        form = BannerForm()
    return render(request, "dashboard/banner_form.html", {"form": form, "form_title": "Create Banner", "submit_label": "Create Banner"})


@staff_member_required(login_url="/accounts/login/")
def create_order(request):
    OrderItemFormSet = inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=1, can_delete=True)
    if request.method == "POST":
        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            # Prepare an order number
            order_number = timezone.now().strftime("ORD%Y%m%d%H%M%S") + f"{random.randint(1000,9999)}"
            order = form.save(commit=False)
            order.order_number = order_number
            # Compute amounts from items
            subtotal = Decimal("0.00")
            # Temporarily set to zero; update after items
            order.subtotal = Decimal("0.00")
            order.gst_amount = Decimal("0.00")
            order.shipping_amount = Decimal("0.00")
            order.total_amount = Decimal("0.00")
            order.save()
            formset.instance = order
            items = formset.save()
            for it in items:
                it.line_total = Decimal(it.unit_price) * it.quantity
                # derive unit_cost from variant.cost_price if available
                try:
                    unit_cost_val = Decimal(str(getattr(it.variant, 'cost_price', 0) or 0))
                except Exception:
                    unit_cost_val = Decimal('0')
                it.unit_cost = unit_cost_val
                it.line_cost = (unit_cost_val * Decimal(it.quantity)).quantize(Decimal('0.01'))
                it.save()
                subtotal += it.line_total
            # Simple totals: GST 18% of subtotal; flat shipping if subtotal < threshold
            from django.conf import settings
            gst_rate = Decimal(str(getattr(settings, "GST_RATE", "0.18")))
            free_threshold = Decimal(str(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)))
            flat_ship = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))
            gst_amount = (subtotal * gst_rate).quantize(Decimal("0.01"))
            shipping_amount = Decimal("0.00") if subtotal >= free_threshold else Decimal(flat_ship)
            total_amount = subtotal + gst_amount + shipping_amount
            order.subtotal = subtotal
            order.gst_amount = gst_amount
            order.shipping_amount = shipping_amount
            order.total_amount = total_amount
            order.save()
            messages.success(request, f"Order {order.order_number} created")
            return redirect("dashboard")
    else:
        form = OrderForm()
        formset = OrderItemFormSet()

    # Build product->variants mapping for client-side filtering
    variant_map = {}
    for v in Variant.objects.select_related("product").all():
        variant_map.setdefault(v.product_id, []).append({
            "id": v.id,
            "text": f"{v.size} / {v.color}",
        })
    variant_map_json = mark_safe(json.dumps(variant_map, cls=DjangoJSONEncoder))
    return render(request, "dashboard/order_form.html", {
        "form": form,
        "formset": formset,
        "variant_map_json": variant_map_json,
        "form_title": "Create Order",
        "submit_label": "Create Order",
    })


@staff_member_required(login_url="/accounts/login/")
def edit_category(request, pk: int):
    obj = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated")
            return redirect("dashboard_categories")
    else:
        form = CategoryForm(instance=obj)
    return render(request, "dashboard/category_form.html", {"form": form, "form_title": "Edit Category", "submit_label": "Save Changes"})


@staff_member_required(login_url="/accounts/login/")
def edit_banner(request, pk: int):
    obj = get_object_or_404(Banner, pk=pk)
    if request.method == "POST":
        form = BannerForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Banner updated")
            return redirect("dashboard_banners")
    else:
        form = BannerForm(instance=obj)
    return render(request, "dashboard/banner_form.html", {"form": form, "form_title": "Edit Banner", "submit_label": "Save Changes"})


@staff_member_required(login_url="/accounts/login/")
def edit_product(request, pk: int):
    product = get_object_or_404(Product, pk=pk)
    ImageFormSet = inlineformset_factory(Product, ProductImage, form=ProductImageForm, extra=0, can_delete=True)
    VideoFormSet = inlineformset_factory(Product, ProductVideo, form=ProductVideoForm, extra=0, can_delete=True)
    VariantFormSet = inlineformset_factory(Product, Variant, form=VariantForm, extra=0, can_delete=True)

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        images_fs = ImageFormSet(request.POST, request.FILES, instance=product, prefix="images")
        videos_fs = VideoFormSet(request.POST, request.FILES, instance=product, prefix="videos")
        variants_fs = VariantFormSet(request.POST, instance=product, prefix="variants")
        if form.is_valid() and images_fs.is_valid() and videos_fs.is_valid() and variants_fs.is_valid():
            from django.db import transaction
            with transaction.atomic():
                form.save()
                images_fs.save()
                videos_fs.save()
                variants_fs.save()
            messages.success(request, "Product updated")
            return redirect("dashboard_products")
    else:
        form = ProductForm(instance=product)
        images_fs = ImageFormSet(instance=product, prefix="images")
        videos_fs = VideoFormSet(instance=product, prefix="videos")
        variants_fs = VariantFormSet(instance=product, prefix="variants")
    # Build variant colors from product's variants
    try:
        var_colors = list(product.variants.values_list('color', flat=True).distinct())
    except Exception:
        var_colors = []
    return render(request, "dashboard/product_form.html", {
        "form": form,
        "images_fs": images_fs,
        "videos_fs": videos_fs,
        "variants_fs": variants_fs,
        "form_title": "Edit Product",
        "submit_label": "Save Changes",
        "variant_colors": var_colors,
    })


@staff_member_required(login_url="/accounts/login/")
def edit_order(request, pk: int):
    order = get_object_or_404(Order, pk=pk)
    OrderItemFormSet = inlineformset_factory(Order, OrderItem, form=OrderItemForm, extra=0, can_delete=True)
    if request.method == "POST":
        form = OrderForm(request.POST, instance=order)
        formset = OrderItemFormSet(request.POST, instance=order)
        if form.is_valid() and formset.is_valid():
            from django.db import transaction
            from django.conf import settings
            from decimal import Decimal
            with transaction.atomic():
                order = form.save()
                items = formset.save()
                subtotal = Decimal("0.00")
                for it in order.items.all():
                    it.line_total = Decimal(it.unit_price) * it.quantity
                    try:
                        unit_cost_val = Decimal(str(getattr(it.variant, 'cost_price', 0) or 0))
                    except Exception:
                        unit_cost_val = Decimal('0')
                    it.unit_cost = unit_cost_val
                    it.line_cost = (unit_cost_val * Decimal(it.quantity)).quantize(Decimal('0.01'))
                    it.save()
                    subtotal += it.line_total
                gst_rate = Decimal(str(getattr(settings, "GST_RATE", "0.18")))
                free_threshold = Decimal(str(getattr(settings, "FREE_SHIPPING_THRESHOLD", 399)))
                flat_ship = Decimal(str(getattr(settings, "FLAT_SHIPPING_RATE", 49)))
                gst_amount = (subtotal * gst_rate).quantize(Decimal("0.01"))
                shipping_amount = Decimal("0.00") if subtotal >= free_threshold else Decimal(flat_ship)
                total_amount = subtotal + gst_amount + shipping_amount
                order.subtotal = subtotal
                order.gst_amount = gst_amount
                order.shipping_amount = shipping_amount
                order.total_amount = total_amount
                order.save()
            messages.success(request, "Order updated")
            return redirect("dashboard_orders")
    else:
        form = OrderForm(instance=order)
        formset = OrderItemFormSet(instance=order)
    # Build variant map for product selection in items
    variant_map = {}
    for v in Variant.objects.select_related("product").all():
        variant_map.setdefault(v.product_id, []).append({
            "id": v.id,
            "text": f"{v.size} / {v.color}",
        })
    variant_map_json = mark_safe(json.dumps(variant_map, cls=DjangoJSONEncoder))
    return render(request, "dashboard/order_form.html", {
        "form": form,
        "formset": formset,
        "variant_map_json": variant_map_json,
        "form_title": "Edit Order",
        "submit_label": "Save Changes",
    })


@staff_member_required(login_url="/accounts/login/")
def coupons_list(request):
    q = request.GET.get("q", "").strip()
    qs = Coupon.objects.all()
    if q:
        qs = qs.filter(code__icontains=q)
    coupons = qs.order_by("-id")[:100]
    return render(request, "dashboard/coupons_list.html", {"coupons": coupons, "q": q})


@staff_member_required(login_url="/accounts/login/")
def products_partial(request):
    q = request.GET.get("q", "").strip()
    qs = Product.objects.select_related("category").all()
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(category__name__icontains=q)
    products = qs.order_by("-created_at")[:100]
    rows_html = render_to_string("dashboard/_products_rows.html", {"products": products}, request=request)
    return JsonResponse({"rows_html": rows_html})


@staff_member_required(login_url="/accounts/login/")
def categories_partial(request):
    q = request.GET.get("q", "").strip()
    qs = Category.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    categories = qs.order_by("name")
    rows_html = render_to_string("dashboard/_categories_rows.html", {"categories": categories}, request=request)
    return JsonResponse({"rows_html": rows_html})


@staff_member_required(login_url="/accounts/login/")
def banners_partial(request):
    q = request.GET.get("q", "").strip()
    qs = Banner.objects.all()
    if q:
        qs = qs.filter(title__icontains=q)
    banners = qs.order_by("sort_order", "-created_at")
    rows_html = render_to_string("dashboard/_banners_rows.html", {"banners": banners}, request=request)
    return JsonResponse({"rows_html": rows_html})


@staff_member_required(login_url="/accounts/login/")
def coupons_partial(request):
    q = request.GET.get("q", "").strip()
    qs = Coupon.objects.all()
    if q:
        qs = qs.filter(code__icontains=q)
    coupons = qs.order_by("-id")[:100]
    rows_html = render_to_string("dashboard/_coupons_rows.html", {"coupons": coupons}, request=request)
    return JsonResponse({"rows_html": rows_html})


@staff_member_required(login_url="/accounts/login/")
def users_list(request):
    User = get_user_model()
    q = request.GET.get("q", "").strip()
    staff = request.GET.get("staff", "all")
    active = request.GET.get("active", "all")
    qs = User.objects.all()
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
    if staff in ("yes", "no"):
        qs = qs.filter(is_staff=(staff == "yes"))
    if active in ("yes", "no"):
        qs = qs.filter(is_active=(active == "yes"))
    users = qs.order_by("-date_joined")[:100]
    ctx = {
        "users": users,
        "q": q,
        "selected_staff": staff,
        "selected_active": active,
        "users_count": User.objects.count(),
        "staff_count": User.objects.filter(is_staff=True).count(),
        "active_count": User.objects.filter(is_active=True).count(),
    }
    return render(request, "dashboard/users_list.html", ctx)


@staff_member_required(login_url="/accounts/login/")
def users_partial(request):
    User = get_user_model()
    q = request.GET.get("q", "").strip()
    staff = request.GET.get("staff", "all")
    active = request.GET.get("active", "all")
    qs = User.objects.all()
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
    if staff in ("yes", "no"):
        qs = qs.filter(is_staff=(staff == "yes"))
    if active in ("yes", "no"):
        qs = qs.filter(is_active=(active == "yes"))
    users = qs.order_by("-date_joined")[:100]
    rows_html = render_to_string("dashboard/_users_rows.html", {"users": users}, request=request)
    return JsonResponse({"rows_html": rows_html})


@staff_member_required(login_url="/accounts/login/")
def user_detail_admin(request, pk: int):
    User = get_user_model()
    user = get_object_or_404(User, pk=pk)
    recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:10]
    total_orders = Order.objects.filter(user=user).count()
    total_spent = Order.objects.filter(user=user, status__in=["paid","shipped","delivered"]).aggregate(s=Sum('total_amount')).get('s') or 0
    addrs = user.addresses.all() if hasattr(user, 'addresses') else []
    profile = getattr(user, 'profile', None)
    from reviews.models import Review
    recent_reviews = Review.objects.filter(user=user).select_related('product').order_by('-created_at')[:5]
    return render(request, 'dashboard/user_detail.html', {
        'u': user,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'addresses': addrs,
        'profile': profile,
        'recent_reviews': recent_reviews,
    })


@staff_member_required(login_url="/accounts/login/")
@require_POST
def toggle_user_staff(request, pk: int):
    User = get_user_model()
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk and user.is_staff:
        # prevent locking yourself out
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'cannot_change_self'}, status=400)
        messages.error(request, "You cannot change your own staff status.")
        return redirect('dashboard_users')
    user.is_staff = not user.is_staff
    user.save(update_fields=['is_staff'])
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'is_staff': user.is_staff})
    return redirect('dashboard_users')


@staff_member_required(login_url="/accounts/login/")
@require_POST
def toggle_user_active(request, pk: int):
    User = get_user_model()
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk and user.is_active:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'cannot_change_self'}, status=400)
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('dashboard_users')
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'is_active': user.is_active})
    return redirect('dashboard_users')


@staff_member_required(login_url="/accounts/login/")
def users_csv(request):
    User = get_user_model()
    q = request.GET.get('q', '').strip()
    qs = User.objects.all()
    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(email__icontains=q)
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="users.csv"'
    import csv
    w = csv.writer(resp)
    w.writerow(['id','username','email','is_staff','is_active','date_joined','last_login'])
    for u in qs.order_by('-date_joined'):
        w.writerow([u.id, u.username, u.email or '', u.is_staff, u.is_active, u.date_joined, u.last_login or ''])
    return resp


@staff_member_required(login_url="/accounts/login/")
def create_coupon(request):
    from .forms import CouponForm
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon created")
            return redirect("dashboard_coupons")
    else:
        form = CouponForm()
    return render(request, "dashboard/coupon_form.html", {"form": form, "form_title": "Create Coupon", "submit_label": "Create Coupon"})


@staff_member_required(login_url="/accounts/login/")
def edit_coupon(request, pk: int):
    from .forms import CouponForm
    obj = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated")
            return redirect("dashboard_coupons")
    else:
        form = CouponForm(instance=obj)
    return render(request, "dashboard/coupon_form.html", {"form": form, "form_title": "Edit Coupon", "submit_label": "Save Changes"})


@staff_member_required(login_url="/accounts/login/")
def delete_coupon(request, pk: int):
    obj = get_object_or_404(Coupon, pk=pk)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Coupon deleted")
        return redirect("dashboard_coupons")
    return render(request, "dashboard/confirm_delete.html", {"object": obj, "object_type": "Coupon", "cancel_url": "/dashboard/coupons/"})


@staff_member_required(login_url="/accounts/login/")
@require_POST
def update_order_status(request, pk: int):
    order = get_object_or_404(Order, pk=pk)
    new_status = request.POST.get("status")
    valid_statuses = {key for key, _ in Order.STATUS_CHOICES}
    if new_status not in valid_statuses:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": False, "error": "invalid_status"}, status=400)
        messages.error(request, "Invalid status selected")
        return redirect("dashboard_orders")
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "status": order.status, "status_display": order.get_status_display()})
    messages.success(request, f"Order {order.order_number} status updated to {order.get_status_display()}")
    return redirect(request.META.get("HTTP_REFERER", "dashboard_orders"))


@staff_member_required(login_url="/accounts/login/")
def delete_product(request, pk: int):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted")
        return redirect("dashboard_products")
    return render(request, "dashboard/confirm_delete.html", {"object": product, "object_type": "Product", "cancel_url": "/dashboard/products/"})


@staff_member_required(login_url="/accounts/login/")
def delete_category(request, pk: int):
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        cat.delete()
        messages.success(request, "Category deleted")
        return redirect("dashboard_categories")
    return render(request, "dashboard/confirm_delete.html", {"object": cat, "object_type": "Category", "cancel_url": "/dashboard/categories/"})


@staff_member_required(login_url="/accounts/login/")
def delete_banner(request, pk: int):
    b = get_object_or_404(Banner, pk=pk)
    if request.method == "POST":
        b.delete()
        messages.success(request, "Banner deleted")
        return redirect("dashboard_banners")
    return render(request, "dashboard/confirm_delete.html", {"object": b, "object_type": "Banner", "cancel_url": "/dashboard/banners/"})


@staff_member_required(login_url="/accounts/login/")
def delete_order(request, pk: int):
    o = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        o.delete()
        messages.success(request, "Order deleted")
        return redirect("dashboard_orders")
    return render(request, "dashboard/confirm_delete.html", {"object": o, "object_type": "Order", "cancel_url": "/dashboard/orders/"})
