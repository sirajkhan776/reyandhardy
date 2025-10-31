from django.urls import path
from . import views


urlpatterns = [
    path("reviews/add/<int:product_id>/", views.add_review, name="add_review"),
    path("reviews/write/<int:product_id>/", views.write_review, name="write_review"),
    path("reviews/product/<slug:slug>/media/", views.product_media, name="product_media"),
    path("reviews/product/<slug:slug>/", views.product_reviews, name="product_reviews"),
]
