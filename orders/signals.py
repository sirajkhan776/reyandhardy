import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order
from django.core.mail import EmailMultiAlternatives
from threading import Thread
from django.template.loader import render_to_string
from django.contrib.sites.models import Site
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


@receiver(post_save, sender=Order)
def notify_new_order_created(sender, instance: Order, created: bool, **kwargs):
    """Send an alert email when a new order is created.

    Emails are sent to ORDER_ALERT_EMAILS (list in settings), or falls back to
    EMAIL_HOST_USER/DEFAULT_FROM_EMAIL when not configured. Best-effort only.
    """
    if not created:
        return
    try:
        recipients = list(getattr(settings, "ORDER_ALERT_EMAILS", []) or [])
        if not recipients:
            fallback = getattr(settings, "EMAIL_HOST_USER", None) or getattr(settings, "DEFAULT_FROM_EMAIL", None)
            if fallback:
                recipients = [fallback]
        if not recipients:
            return

        try:
            site = Site.objects.get_current()
            site_name = site.name
            site_domain = site.domain
        except Exception:
            site_name = getattr(settings, "STORE_NAME", "Store")
            site_domain = getattr(settings, "STORE_DOMAIN", "localhost:8000")

        ctx = {
            "order": instance,
            "items": list(instance.items.all()),
            "CURRENCY_SYMBOL": getattr(settings, "CURRENCY_SYMBOL", "₹"),
            "site_name": site_name,
            "site_domain": site_domain,
            "dashboard_url": f"https://{site_domain}/dashboard/orders/{instance.pk}/",
        }

        subject = render_to_string("orders/email/new_order_staff_subject.txt", ctx).strip()
        text_body = render_to_string("orders/email/new_order_staff.txt", ctx)
        html_body = render_to_string("orders/email/new_order_staff.html", ctx)

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or None
        msg = EmailMultiAlternatives(subject, text_body, from_email, recipients)
        msg.attach_alternative(html_body, "text/html")
        # Send asynchronously to avoid blocking request thread on SMTP connect
        def _send(m):
            try:
                m.send(fail_silently=True)
            except Exception:
                logger.exception("Email send failed for order %s", instance.order_number)
        Thread(target=_send, args=(msg,), daemon=True).start()
    except Exception:
        logger.exception("Failed to send new-order alert for %s", instance.order_number)
