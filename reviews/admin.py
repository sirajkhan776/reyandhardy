from django.contrib import admin
from .models import Review, ReviewMedia


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")


@admin.register(ReviewMedia)
class ReviewMediaAdmin(admin.ModelAdmin):
    list_display = ("review", "kind", "created_at")
    list_filter = ("kind", "created_at")
