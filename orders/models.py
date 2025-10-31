from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from catalog.models import Product, Variant


class Order(models.Model):
    PAYMENT_METHODS = [
        ("razorpay", "Razorpay"),
        ("cod", "Cash on Delivery"),
    ]
    STATUS_CHOICES = [
        ("created", "Placed"),
        ("paid", "Paid"),
        ("confirmed", "Confirmed"),
        ("packed", "Packed"),
        ("dispatched", "Dispatched"),
        ("out_for_delivery", "Out for delivery"),
        ("delivered", "Delivered"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("return_requested", "Return requested"),
        ("exchange_requested", "Exchange requested"),
        ("return_in_transit", "Return in transit"),
        ("return_completed", "Return completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    payment_method = models.CharField(max_length=12, choices=PAYMENT_METHODS)
    razorpay_order_id = models.CharField(max_length=200, blank=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True)
    razorpay_signature = models.CharField(max_length=200, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=30, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    shipping_name = models.CharField(max_length=200)
    shipping_phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")

    shipping_provider = models.CharField(max_length=100, default="Shiprocket")
    tracking_number = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_number} ({self.user})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(Variant, null=True, blank=True, on_delete=models.PROTECT)
    # Snapshot of selected variant attributes for display, even if relation is null/changed later
    variant_size = models.CharField(max_length=10, blank=True)
    variant_color = models.CharField(max_length=30, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    # Snapshot cost at time of order
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    line_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.product} x {self.quantity}"


class ReturnRequest(models.Model):
    TYPES = [("return", "Return"), ("exchange", "Exchange")]
    STATUSES = [
        ("requested", "Requested"),
        ("approved", "Approved"),
        ("pickup_scheduled", "Pickup scheduled"),
        ("in_transit", "In transit"),
        ("completed", "Completed"),
        ("rejected", "Rejected"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="returns")
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    type = models.CharField(max_length=10, choices=TYPES)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="requested")
    awb_code = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_type_display()} for {self.order.order_number} ({self.status})"


class ReturnItem(models.Model):
    request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="items")
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    # For exchange to a different variant
    exchange_variant = models.ForeignKey(Variant, null=True, blank=True, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.order_item} -> {self.exchange_variant or '-'}"
