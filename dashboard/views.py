from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, F
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.utils import timezone
from decimal import Decimal
import random

from orders.models import Order, OrderItem
from catalog.models import Variant, Product, Category, ProductImage, ProductVideo
from core.models import Banner
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

    top_products = (
        OrderItem.objects
        .values(name=F("product__name"))
        .annotate(qty=Sum("quantity"), sales=Sum("line_total"))
        .order_by("-qty")[:10]
    )

    stock_summary = Variant.objects.aggregate(total_qty=Sum("stock"))

    return render(request, "dashboard/index.html", {
        "revenue": revenue,
        "top_products": top_products,
        "stock_total": stock_summary["total_qty"] or 0,
        "orders_count": Order.objects.count(),
    })


@staff_member_required(login_url="/accounts/login/")
def orders_list(request):
    orders = Order.objects.order_by("-created_at")[:50]
    return render(request, "dashboard/orders_list.html", {"orders": orders})


@staff_member_required(login_url="/accounts/login/")
def products_list(request):
    products = Product.objects.select_related("category").order_by("-created_at")[:50]
    return render(request, "dashboard/products_list.html", {"products": products})


@staff_member_required(login_url="/accounts/login/")
def categories_list(request):
    categories = Category.objects.order_by("name")
    return render(request, "dashboard/categories_list.html", {"categories": categories})


@staff_member_required(login_url="/accounts/login/")
def banners_list(request):
    banners = Banner.objects.order_by("sort_order", "-created_at")
    return render(request, "dashboard/banners_list.html", {"banners": banners})


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
        images_fs = ImageFormSet(request.POST, request.FILES, prefix="images")
        videos_fs = VideoFormSet(request.POST, request.FILES, prefix="videos")
        variants_fs = VariantFormSet(request.POST, prefix="variants")
        if form.is_valid() and images_fs.is_valid() and videos_fs.is_valid() and variants_fs.is_valid():
            product = form.save()
            images_fs.instance = product
            videos_fs.instance = product
            variants_fs.instance = product
            images_fs.save()
            videos_fs.save()
            variants_fs.save()
            messages.success(request, "Product created")
            return redirect("dashboard_products")
    else:
        form = ProductForm()
        images_fs = ImageFormSet(prefix="images")
        videos_fs = VideoFormSet(prefix="videos")
        variants_fs = VariantFormSet(prefix="variants")
    return render(request, "dashboard/product_form.html", {
        "form": form,
        "images_fs": images_fs,
        "videos_fs": videos_fs,
        "variants_fs": variants_fs,
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
    return render(request, "dashboard/banner_form.html", {"form": form})


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
    })
