import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Iterable, List

import requests
from django.conf import settings

from .models import Order, OrderItem


logger = logging.getLogger(__name__)

_SR_BASE = "https://apiv2.shiprocket.in/v1/external"
_token: Optional[str] = None
_token_expiry_ts: float = 0.0


def _enabled() -> bool:
    if not getattr(settings, "SHIPROCKET_ENABLED", False):
        return False
    # Require minimum credentials
    return bool(settings.SHIPROCKET_EMAIL and settings.SHIPROCKET_PASSWORD and settings.SHIPROCKET_PICKUP_LOCATION)


def _auth_headers() -> Dict[str, str]:
    token = _get_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_token() -> str:
    global _token, _token_expiry_ts
    now = time.time()
    if _token and now < _token_expiry_ts:
        return _token
    email = settings.SHIPROCKET_EMAIL
    password = settings.SHIPROCKET_PASSWORD
    resp = requests.post(f"{_SR_BASE}/auth/login", json={"email": email, "password": password}, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    _token = data.get("token")
    # Token TTL is typically 10 min; refresh slightly earlier
    _token_expiry_ts = now + 9 * 60
    if not _token:
        raise RuntimeError("Shiprocket auth failed: token missing")
    return _token


def _format_order_items(order: Order):
    items = []
    for it in order.items.select_related("product", "variant").all():
        name = str(it.product)
        if it.variant:
            name = f"{name} - {it.variant.size}/{it.variant.color}"
        sku = it.variant.sku if it.variant else f"SKU-{it.product.id}"
        items.append(
            {
                "name": name,
                "sku": sku,
                "units": int(it.quantity),
                "selling_price": float(it.unit_price),
            }
        )
    return items


def _order_subtotal_from_items(order: Order) -> Decimal:
    total = Decimal("0.00")
    for it in order.items.all():
        total += it.line_total
    return total


def create_shiprocket_shipment(order: Order) -> Optional[str]:
    """Create a Shiprocket order + assign AWB. Returns AWB code or None.

    Safe no-op if Shiprocket not enabled or already has tracking number.
    """
    try:
        if not _enabled():
            logger.info("Shiprocket disabled or not configured; skipping for %s", order.order_number)
            return None
        if order.tracking_number:
            logger.info("Order %s already has tracking: %s", order.order_number, order.tracking_number)
            return order.tracking_number

        # Build order payload
        order_date = (order.created_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")
        items = _format_order_items(order)
        units_total = sum(i["units"] for i in items)
        # Compute weight and dims from order items where available
        total_weight_dec = Decimal("0.00")
        max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
        max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
        max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
        for it in order.items.select_related("product", "variant").all():
            w = None
            if it.variant and getattr(it.variant, "weight_kg", None):
                w = Decimal(str(it.variant.weight_kg))
            elif getattr(it.product, "weight_kg", None):
                w = Decimal(str(it.product.weight_kg))
            else:
                w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
            total_weight_dec += (w * Decimal(it.quantity))
            lv = (getattr(it.variant, "length_cm", None) if it.variant else None) or getattr(it.product, "length_cm", None)
            bv = (getattr(it.variant, "breadth_cm", None) if it.variant else None) or getattr(it.product, "breadth_cm", None)
            hv = (getattr(it.variant, "height_cm", None) if it.variant else None) or getattr(it.product, "height_cm", None)
            if lv:
                try: max_l = max(max_l, int(lv))
                except Exception: pass
            if bv:
                try: max_b = max(max_b, int(bv))
                except Exception: pass
            if hv:
                try: max_h = max(max_h, int(hv))
                except Exception: pass
        total_weight = float(total_weight_dec)

        l = max_l
        b = max_b
        h = max_h

        payment_method = "Prepaid" if order.payment_method == "razorpay" else "COD"
        sub_total = float(_order_subtotal_from_items(order))

        payload: Dict[str, Any] = {
            "order_id": order.order_number,
            "order_date": order_date,
            "pickup_location": settings.SHIPROCKET_PICKUP_LOCATION,
            "channel_id": settings.SHIPROCKET_CHANNEL_ID or None,
            "billing_customer_name": order.shipping_name or order.user.get_full_name() or order.user.username,
            "billing_last_name": "",
            "billing_address": f"{order.address_line1} {order.address_line2}".strip(),
            "billing_city": order.city,
            "billing_pincode": order.postal_code,
            "billing_state": order.state,
            "billing_country": order.country or "India",
            "billing_email": getattr(order.user, "email", "") or "",
            "billing_phone": order.shipping_phone,
            # Shipping same as billing
            "shipping_is_billing": True,
            "order_items": items,
            "payment_method": payment_method,
            "sub_total": sub_total,
            "length": l,
            "breadth": b,
            "height": h,
            "weight": total_weight,
        }
        # Remove nulls
        payload = {k: v for k, v in payload.items() if v is not None}

        # Create order in Shiprocket
        resp = requests.post(f"{_SR_BASE}/orders/create/adhoc", json=payload, headers=_auth_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        shipment_id = data.get("shipment_id") or (data.get("data") or {}).get("shipment_id")
        if not shipment_id:
            logger.warning("Shiprocket create order did not return shipment_id for %s: %s", order.order_number, data)
            return None

        # Assign AWB (auto-assign best courier)
        awb = _assign_awb(shipment_id)
        if awb:
            order.tracking_number = awb
            order.shipping_provider = "Shiprocket"
            order.save(update_fields=["tracking_number", "shipping_provider", "updated_at"])
        return awb
    except requests.HTTPError as http_err:
        logger.exception("Shiprocket HTTP error for %s: %s", order.order_number, http_err)
    except Exception as e:
        logger.exception("Shiprocket error for %s: %s", order.order_number, e)
    return None


def _assign_awb(shipment_id: Any) -> Optional[str]:
    try:
        resp = requests.post(
            f"{_SR_BASE}/courier/assign/awb",
            json={"shipment_id": shipment_id},
            headers=_auth_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Different accounts may return under different keys; try common ones
        awb = data.get("awb_code") or (data.get("data") or {}).get("awb_code")
        return str(awb) if awb else None
    except Exception:
        logger.exception("Failed assigning AWB for shipment_id=%s", shipment_id)
        return None


def estimate_shipping_charge(
    drop_pin: str,
    units_total: int,
    cod: bool = False,
    declared_value: Optional[Decimal] = None,
    total_weight_kg: Optional[Decimal] = None,
    dims_cm: Optional[tuple[int, int, int]] = None,
) -> Optional[Decimal]:
    """Estimate shipping charge using Shiprocket serviceability API.

    Returns the cheapest available rate as Decimal, or None on failure.
    Requires SHIPROCKET_ENABLED and SHIPROCKET_PICKUP_PIN to be configured.
    """
    try:
        if not _enabled():
            return None
        pickup_pin = getattr(settings, "SHIPROCKET_PICKUP_PIN", "")
        if not pickup_pin or not drop_pin:
            return None
        if total_weight_kg is not None:
            weight = float(Decimal(total_weight_kg))
        else:
            unit_weight = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
            weight = float((unit_weight * Decimal(max(1, int(units_total)))))
        if dims_cm is not None:
            l, b, h = dims_cm
        else:
            l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
            b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
            h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
        payload: Dict[str, Any] = {
            "pickup_postcode": str(pickup_pin),
            "delivery_postcode": str(drop_pin),
            "weight": weight,
            "cod": 1 if cod else 0,
            "length": l,
            "breadth": b,
            "height": h,
        }
        if declared_value is not None:
            try:
                payload["declared_value"] = float(declared_value)
            except Exception:
                pass
        resp = requests.post(f"{_SR_BASE}/courier/serviceability/", json=payload, headers=_auth_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        companies: Iterable[Dict[str, Any]] = (
            (data.get("data") or {}).get("available_courier_companies")
            or data.get("available_courier_companies")
            or []
        )
        rates: list[Decimal] = []
        for c in companies:
            rate = c.get("rate")
            if rate is None:
                # fallback fields sometimes present
                rate = c.get("freight_charge") or c.get("total_amount")
            try:
                if rate is not None:
                    rates.append(Decimal(str(rate)))
            except Exception:
                continue
        if not rates:
            return None
        return min(rates)
    except Exception:
        logger.exception("Shiprocket rate estimate failed for drop_pin=%s", drop_pin)
        return None


def track_awb(awb_code: str) -> Optional[Dict[str, Any]]:
    """Fetch tracking details for an AWB via Shiprocket serviceability tracking API.
    Returns a dict with current status and a list of scans when available.
    """
    try:
        if not _enabled() or not awb_code:
            return None
        resp = requests.get(f"{_SR_BASE}/courier/track/awb/{awb_code}", headers=_auth_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json() or {}
        # Normalize common fields
        track_data = data.get("tracking_data") or data
        shipment_status = (track_data.get("shipment_status") or track_data.get("current_status"))
        scans = (track_data.get("shipment_track") or track_data.get("scan") or [])
        return {"status": shipment_status, "events": scans}
    except Exception:
        logger.exception("Failed to fetch AWB tracking for %s", awb_code)
        return None


def create_shiprocket_return(order: Order, items: List[OrderItem]) -> Optional[str]:
    """Create a Shiprocket return (reverse pickup) for given order items.
    Returns return AWB code on success.
    """
    try:
        if not _enabled():
            return None
        # Build return order payload — mirror original shipment, customer address is pickup here
        order_date = (order.created_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")
        line_items = []
        units_total = 0
        total_weight_dec = Decimal("0.00")
        max_l = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_LCM", 20))
        max_b = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_BCM", 15))
        max_h = int(getattr(settings, "SHIPROCKET_DEFAULT_DIM_HCM", 2))
        for it in items:
            name = str(it.product)
            if it.variant:
                name = f"{name} - {it.variant.size}/{it.variant.color}"
            sku = it.variant.sku if it.variant else f"SKU-{it.product.id}"
            qty = int(it.quantity)
            units_total += qty
            line_items.append({"name": name, "sku": sku, "units": qty, "selling_price": float(it.unit_price)})
            # weight/dims
            w = None
            if it.variant and getattr(it.variant, "weight_kg", None):
                w = Decimal(str(it.variant.weight_kg))
            elif getattr(it.product, "weight_kg", None):
                w = Decimal(str(it.product.weight_kg))
            else:
                w = Decimal(str(getattr(settings, "SHIPROCKET_DEFAULT_UNIT_WEIGHT_KG", 0.5)))
            total_weight_dec += (w * Decimal(qty))
            lv = (getattr(it.variant, "length_cm", None) if it.variant else None) or getattr(it.product, "length_cm", None)
            bv = (getattr(it.variant, "breadth_cm", None) if it.variant else None) or getattr(it.product, "breadth_cm", None)
            hv = (getattr(it.variant, "height_cm", None) if it.variant else None) or getattr(it.product, "height_cm", None)
            if lv:
                try: max_l = max(max_l, int(lv))
                except Exception: pass
            if bv:
                try: max_b = max(max_b, int(bv))
                except Exception: pass
            if hv:
                try: max_h = max(max_h, int(hv))
                except Exception: pass
        total_weight = float(total_weight_dec)

        payload = {
            "order_id": f"RET-{order.order_number}",
            "order_date": order_date,
            "pickup_customer_name": order.shipping_name,
            "pickup_last_name": "",
            "pickup_address": f"{order.address_line1} {order.address_line2}".strip(),
            "pickup_city": order.city,
            "pickup_pincode": order.postal_code,
            "pickup_state": order.state,
            "pickup_country": order.country or "India",
            "pickup_email": getattr(order.user, "email", "") or "",
            "pickup_phone": order.shipping_phone,
            "pickup_isd_code": "91",
            # Delivery back to warehouse (Shiprocket pickup location)
            "delivery_customer_name": settings.SHIPROCKET_PICKUP_LOCATION or "Warehouse",
            "delivery_last_name": "",
            "delivery_address": settings.SHIPROCKET_PICKUP_LOCATION,
            "delivery_city": "",
            "delivery_pincode": getattr(settings, "SHIPROCKET_PICKUP_PIN", ""),
            "delivery_state": "",
            "delivery_country": "India",
            "delivery_email": getattr(order.user, "email", "") or "",
            "delivery_phone": order.shipping_phone,
            "order_items": line_items,
            "length": max_l,
            "breadth": max_b,
            "height": max_h,
            "weight": total_weight,
        }
        resp = requests.post(f"{_SR_BASE}/orders/create/return", json=payload, headers=_auth_headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Some accounts return awb_code directly
        awb = data.get("awb_code") or (data.get("data") or {}).get("awb_code")
        if awb:
            return str(awb)
        # In some cases need to assign separately using shipment_id
        shipment_id = data.get("shipment_id") or (data.get("data") or {}).get("shipment_id")
        if shipment_id:
            return _assign_awb(shipment_id)
        return None
    except Exception:
        logger.exception("Failed to create Shiprocket return for %s", order.order_number)
        return None
