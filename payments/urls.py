from django.urls import path
from . import views


urlpatterns = [
    path("payments/razorpay/callback/", views.razorpay_callback, name="razorpay_callback"),
    path("payments/razorpay/webhook/", views.razorpay_webhook, name="razorpay_webhook"),
]

