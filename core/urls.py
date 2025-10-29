from django.urls import path
from . import views

urlpatterns = [
    path("subscribe/", views.newsletter_subscribe, name="newsletter_subscribe"),
]

