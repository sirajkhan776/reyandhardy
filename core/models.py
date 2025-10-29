from django.db import models


class Banner(models.Model):
    title = models.CharField(max_length=120, blank=True)
    subtitle = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to="banners/", blank=True, null=True, help_text="Optional image for hero carousel")
    video = models.FileField(upload_to="banners/videos/", blank=True, null=True, help_text="Optional video for hero carousel (MP4/WebM)")
    link_url = models.URLField(blank=True, help_text="Optional link target when clicking the banner")
    button_text = models.CharField(max_length=40, blank=True, default="Shop now")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("sort_order", "-created_at")

    def __str__(self):
        return self.title or f"Banner #{self.id}"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
