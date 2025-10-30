from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Product
from accounts.notifications import broadcast


@receiver(post_save, sender=Product)
def product_notify(sender, instance: Product, created: bool, **kwargs):
    try:
        if created and instance.notify_users:
            title = f"New arrival: {instance.name}"
            link = f"/product/{instance.slug}/"
            broadcast(title=title, message="Check it out before it sells out!", link_url=link, level="promo")
        elif not created and instance.notify_users and instance.sale_price is not None:
            title = f"On sale: {instance.name}"
            link = f"/product/{instance.slug}/"
            broadcast(title=title, message="Limited time offer.", link_url=link, level="promo")
    except Exception:
        # Fail silently; notifications shouldn't break product saving
        pass

