from django.db import models
from django.utils import timezone


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=200, blank=True)
    discount_percent = models.PositiveIntegerField(help_text="e.g., 10 for 10%")
    active = models.BooleanField(default=True)
    notify_users = models.BooleanField(default=False, help_text="Notify users when this offer is added")
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    def is_valid(self) -> bool:
        if not self.active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_to and now > self.valid_to:
            return False
        return True

    def __str__(self):
        return f"{self.code} ({self.discount_percent}% off)"
