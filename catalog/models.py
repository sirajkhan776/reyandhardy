from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from decimal import Decimal


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_display = models.BooleanField(default=False, help_text="Show this category on home page")
    thumbnail = models.ImageField(upload_to="categories/", blank=True, null=True, help_text="Upload thumbnail for home chips")
    thumbnail_url = models.URLField(blank=True, help_text="(Optional) External image URL for thumbnail on home")

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)  # price before discounts
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_best_seller = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # Shipping attributes (fallbacks when variant-level absent)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, help_text="Weight per unit in kg")
    length_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Package length in cm")
    breadth_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Package breadth in cm")
    height_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Package height in cm")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def price(self) -> Decimal:
        return self.sale_price if self.sale_price is not None else self.base_price

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.product.name}"


class Variant(models.Model):
    SIZE_CHOICES = [
        ("M", "M"),
        ("L", "L"),
        ("XL", "XL"),
        ("XXL", "XXL"),
    ]
    COLOR_CHOICES = [
        ("Red", "Red"),
        ("Black", "Black"),
        ("Navy Blue", "Navy Blue"),
        ("White", "White"),
        ("Grey", "Grey"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size = models.CharField(max_length=4, choices=SIZE_CHOICES)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES)
    sku = models.CharField(max_length=50, unique=True)
    stock = models.PositiveIntegerField(default=0)
    # Cost of goods per unit (for profit analytics). Optional; defaults to 0.
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Optional per-variant shipping attributes
    weight_kg = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True, help_text="Weight per unit in kg")
    length_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Package length in cm")
    breadth_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Package breadth in cm")
    height_cm = models.PositiveIntegerField(null=True, blank=True, help_text="Package height in cm")

    class Meta:
        unique_together = ("product", "size", "color")

    def __str__(self):
        return f"{self.product.name} - {self.size} / {self.color}"


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")

    def __str__(self):
        return f"{self.user} ❤ {self.product}"


class ProductVideo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="videos")
    video = models.FileField(upload_to="products/videos/", help_text="Short clip (MP4/WebM)")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video for {self.product.name}"
