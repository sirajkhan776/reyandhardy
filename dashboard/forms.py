from django import forms
from django.contrib.auth import get_user_model

from catalog.models import Category, Product, ProductImage, ProductVideo, Variant
from core.models import Banner
from orders.models import Order, OrderItem
from coupons.models import Coupon


class _BootstrapFormMixin:
    def _apply_bootstrap(self):
        for name, field in self.fields.items():
            widget = field.widget
            base = widget.attrs.get("class", "")
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (base + " form-select").strip()
            elif isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs["class"] = (base + " form-check-input").strip()
            else:
                widget.attrs["class"] = (base + " form-control").strip()
            # Placeholders for common fields
            if name in {"name", "title"}:
                widget.attrs.setdefault("placeholder", field.label)
            if name in {"base_price", "sale_price", "unit_price"}:
                widget.attrs.setdefault("step", "0.01")
            if name in {"shipping_phone"}:
                widget.attrs.setdefault("inputmode", "tel")


class CategoryForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "is_display", "thumbnail", "thumbnail_url"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        self.fields["thumbnail"].required = False
        self.fields["thumbnail_url"].required = False


class ProductForm(_BootstrapFormMixin, forms.ModelForm):
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
            "notify_users",
            # Measurements
            "weight_kg",
            "length_cm",
            "breadth_cm",
            "height_cm",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        self.fields["description"].widget.attrs.setdefault("rows", 4)


class BannerForm(_BootstrapFormMixin, forms.ModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        self.fields["image"].required = False
        self.fields["video"].required = False
        self.fields["subtitle"].widget.attrs.setdefault("placeholder", "Optional subtitle")
        self.fields["link_url"].widget.attrs.setdefault("placeholder", "https://…")


class OrderForm(_BootstrapFormMixin, forms.ModelForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()


class OrderItemForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ["product", "variant", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        self.fields["quantity"].widget.attrs.setdefault("min", 1)


class CouponForm(_BootstrapFormMixin, forms.ModelForm):
    # Use HTML5 datetime-local and accept ISO-like input with 'T'
    valid_from = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
    )
    valid_to = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        input_formats=["%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"],
    )

    class Meta:
        model = Coupon
        fields = [
            "code",
            "description",
            "discount_percent",
            "active",
            "notify_users",
            "valid_from",
            "valid_to",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()

    def clean(self):
        cleaned = super().clean()
        vf = cleaned.get("valid_from")
        vt = cleaned.get("valid_to")
        if vf and vt and vt < vf:
            self.add_error("valid_to", "Valid to must be after valid from")
        return cleaned


class ProductImageForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "is_primary", "color"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        # Hint mobile to show image picker/camera
        try:
            self.fields["image"].widget.attrs.setdefault("accept", "image/*")
        except Exception:
            pass
        try:
            self.fields["color"].widget.attrs.setdefault("placeholder", "Optional: assign to variant color (e.g., Black)")
            self.fields["color"].widget.attrs.setdefault("list", "variantColorOptions")
        except Exception:
            pass


class ProductVideoForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProductVideo
        fields = ["video"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        try:
            self.fields["video"].widget.attrs.setdefault("accept", "video/*")
            # Do NOT set 'capture' so mobile opens gallery/picker instead of camera
            self.fields["video"].widget.attrs.pop("capture", None)
        except Exception:
            pass


class VariantForm(_BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Variant
        fields = [
            "size",
            "color",
            "sku",
            "stock",
            # Retail price at variant level (optional)
            "base_price",
            "sale_price",
            # Optional per-variant measurements
            "cost_price",
            "weight_kg",
            "length_cm",
            "breadth_cm",
            "height_cm",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap()
        try:
            # Provide suggestions for color via datalist defined on the page
            self.fields["color"].widget.attrs.setdefault("list", "variantColorOptions")
            self.fields["color"].widget.attrs.setdefault("placeholder", "e.g., Black, Blue, Green")
        except Exception:
            pass
