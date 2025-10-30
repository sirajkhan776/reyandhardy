from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="India")
    interests = models.CharField(max_length=255, blank=True, help_text="Comma separated interests")

    def __str__(self):
        return f"Profile of {self.user.username}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_default", "-updated_at")

    def __str__(self):
        return f"{self.full_name} ({self.city})"


class Notification(models.Model):
    LEVELS = (
        ("info", "Info"),
        ("promo", "Promotion"),
        ("alert", "Alert"),
    )
    # If user is null -> broadcast to all users
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=500, blank=True)
    link_url = models.CharField(max_length=300, blank=True)
    level = models.CharField(max_length=12, choices=LEVELS, default="info")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        tgt = self.user.username if self.user_id else "ALL"
        return f"{self.title} -> {tgt}"


class NotificationRead(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications_read")
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="reads")
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "notification")

    def __str__(self):
        return f"Read {self.notification_id} by {self.user_id}"
