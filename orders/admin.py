from django.contrib import admin
from django.contrib import messages
from .models import Order, OrderItem, ReturnRequest, ReturnItem
from .shiprocket import create_shiprocket_shipment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = (
        "product",
        "variant",
        "variant_size",
        "variant_color",
        "quantity",
        "unit_price",
        "line_total",
        "unit_cost",
        "line_cost",
    )
    readonly_fields = ("unit_price", "line_total", "unit_cost", "line_cost")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "user", "status", "payment_method", "total_amount", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("order_number", "user__username", "tracking_number")
    inlines = [OrderItemInline]
    actions = ["create_shiprocket_shipments"]

    def create_shiprocket_shipments(self, request, queryset):
        created = 0
        skipped = 0
        for order in queryset:
            if order.tracking_number:
                skipped += 1
                continue
            awb = create_shiprocket_shipment(order)
            if awb:
                created += 1
            else:
                skipped += 1
        if created:
            self.message_user(request, f"Created Shiprocket shipments: {created}", level=messages.SUCCESS)
        if skipped:
            self.message_user(request, f"Skipped: {skipped}", level=messages.INFO)
    create_shiprocket_shipments.short_description = "Create Shiprocket shipment for selected orders"


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "type", "status", "awb_code", "created_at")
    list_filter = ("type", "status", "created_at")
    search_fields = ("order__order_number", "user__username", "awb_code")
