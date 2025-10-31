from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from catalog.models import Product, Variant


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    updated_at = models.DateTimeField(auto_now=True)

    def subtotal(self) -> Decimal:
        return sum((item.line_total() for item in self.items.all()), Decimal("0.00"))

    def __str__(self):
        return f"Cart({self.user})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("cart", "product", "variant")

    def unit_price(self) -> Decimal:
        if self.variant and (getattr(self.variant, "sale_price", None) is not None or getattr(self.variant, "base_price", None) is not None):
            return self.variant.price()
        return self.product.price()

    def line_total(self) -> Decimal:
        return self.unit_price() * self.quantity

    def __str__(self):
        return f"{self.product} x {self.quantity}"
