import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order
from .shiprocket import create_shiprocket_shipment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def create_shiprocket_on_paid(sender, instance: Order, created: bool, **kwargs):
    # Auto-create shipment only when order is paid and Shiprocket is enabled
    try:
        if not getattr(settings, "SHIPROCKET_ENABLED", False):
            return
        if instance.status != "paid":
            return
        if instance.tracking_number:
            return
        # Best-effort; do not raise exceptions
        create_shiprocket_shipment(instance)
    except Exception:
        logger.exception("Error in Shiprocket post-save handler for %s", instance.order_number)

