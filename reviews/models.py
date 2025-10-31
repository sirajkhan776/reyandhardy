from django.db import models
from django.contrib.auth.models import User
from catalog.models import Product
import mimetypes


class Review(models.Model):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")

    def __str__(self):
        return f"{self.product} - {self.rating}⭐ by {self.user}"


class ReviewMedia(models.Model):
    KIND_CHOICES = (
        ("image", "Image"),
        ("video", "Video"),
    )

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="reviews/%Y/%m/%d/")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.kind:
            ctype, _ = mimetypes.guess_type(self.file.name)
            if ctype and ctype.startswith("image/"):
                self.kind = "image"
            elif ctype and ctype.startswith("video/"):
                self.kind = "video"
            else:
                # Default to image if unknown; upstream validation should prevent this
                self.kind = "image"
        return super().save(*args, **kwargs)

    @property
    def is_image(self):
        return self.kind == "image"

    @property
    def is_video(self):
        return self.kind == "video"

    def __str__(self):
        return f"{self.kind} for review {self.review_id}"
