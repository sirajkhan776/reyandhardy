from django import forms
from django.contrib.auth import get_user_model

from catalog.models import Category, Product
from core.models import Banner
from orders.models import Order, OrderItem


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "is_display", "thumbnail", "thumbnail_url"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "base_price",
            "sale_price",
            "is_active",
            "is_best_seller",
        ]


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = [
            "title",
            "subtitle",
            "image",
            "video",
            "link_url",
            "button_text",
            "is_active",
            "sort_order",
        ]


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "user",
            "status",
            "payment_method",
            "shipping_name",
            "shipping_phone",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "country",
            "shipping_provider",
            "tracking_number",
        ]


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "variant", "quantity", "unit_price"]

