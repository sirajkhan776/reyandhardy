from django.contrib.auth.models import User
from .models import Notification


def broadcast(title: str, message: str = "", link_url: str = "", level: str = "promo") -> Notification:
    """Create a broadcast notification to all users.

    Use user=None on Notification; unread state is tracked per-user via NotificationRead entries when opened/marked.
    """
    return Notification.objects.create(user=None, title=title, message=message, link_url=link_url, level=level)


def notify_user(user: User, title: str, message: str = "", link_url: str = "", level: str = "info") -> Notification:
    return Notification.objects.create(user=user, title=title, message=message, link_url=link_url, level=level)

