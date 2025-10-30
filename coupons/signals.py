from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Coupon
from accounts.notifications import broadcast


@receiver(post_save, sender=Coupon)
def coupon_notify(sender, instance: Coupon, created: bool, **kwargs):
    try:
        if created and instance.notify_users and instance.is_valid():
            title = f"New offer: {instance.code} — {instance.discount_percent}% off"
            broadcast(title=title, message=instance.description or "Limited time offer.", link_url="/", level="promo")
    except Exception:
        pass

