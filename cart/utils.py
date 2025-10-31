from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Any

from catalog.models import Product, Variant


SESSION_KEY = "cart"
COUPON_KEY = "coupon"


@dataclass
class SessionCartItem:
    product: Product
    variant: Optional[Variant]
    quantity: int

    def unit_price(self) -> Decimal:
        if self.variant and (getattr(self.variant, "sale_price", None) is not None or getattr(self.variant, "base_price", None) is not None):
            try:
                return self.variant.price()
            except Exception:
                pass
        return self.product.price()

    def line_total(self) -> Decimal:
        return self.unit_price() * self.quantity


def _get_session_cart(request) -> Dict[str, Any]:
    cart = request.session.get(SESSION_KEY)
    if not cart or "items" not in cart:
        cart = {"items": []}
        request.session[SESSION_KEY] = cart
    return cart


def add_session_item(request, product_id: int, variant_id: Optional[int], quantity: int = 1):
    cart = _get_session_cart(request)
    items = cart["items"]
    # merge by product+variant
    for it in items:
        if it.get("product_id") == product_id and it.get("variant_id") == variant_id:
            it["quantity"] = int(it.get("quantity", 1)) + int(quantity)
            request.session.modified = True
            return
    items.append({"product_id": product_id, "variant_id": variant_id, "quantity": int(quantity)})
    request.session.modified = True


def update_session_item(request, product_id: int, variant_id: Optional[int], quantity: int):
    cart = _get_session_cart(request)
    for it in cart["items"]:
        if it.get("product_id") == product_id and it.get("variant_id") == variant_id:
            it["quantity"] = max(1, int(quantity))
            request.session.modified = True
            return


def remove_session_item(request, product_id: int, variant_id: Optional[int]):
    cart = _get_session_cart(request)
    cart["items"] = [
        it for it in cart["items"] if not (it.get("product_id") == product_id and it.get("variant_id") == variant_id)
    ]
    request.session.modified = True


def clear_session_cart(request):
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


def get_session_items(request) -> List[SessionCartItem]:
    items: List[SessionCartItem] = []
    cart = _get_session_cart(request)
    for it in cart.get("items", []):
        try:
            product = Product.objects.get(id=it.get("product_id"))
        except Product.DoesNotExist:
            continue
        variant = None
        vid = it.get("variant_id")
        if vid:
            try:
                variant = Variant.objects.get(id=vid)
            except Variant.DoesNotExist:
                variant = None
        qty = max(1, int(it.get("quantity", 1)))
        items.append(SessionCartItem(product=product, variant=variant, quantity=qty))
    return items


# Coupon helpers
def set_session_coupon(request, code: str):
    request.session[COUPON_KEY] = {"code": code}
    request.session.modified = True


def get_session_coupon(request) -> Optional[str]:
    data = request.session.get(COUPON_KEY)
    if isinstance(data, dict):
        return data.get("code")
    return None


def clear_session_coupon(request):
    request.session.pop(COUPON_KEY, None)
    request.session.modified = True
