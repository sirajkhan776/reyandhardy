from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, F
from django.shortcuts import render
from orders.models import Order, OrderItem
from catalog.models import Variant


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
