from django.urls import path
from . import views


urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("orders/", views.order_list, name="order_list"),
    path("order/<str:order_number>/", views.order_detail, name="order_detail"),
    path("order/<str:order_number>/help/", views.order_support, name="order_support"),
    path("order/<str:order_number>/invoice/", views.order_invoice, name="order_invoice"),
    path("order/<str:order_number>/track/", views.order_track, name="order_track"),
    path("order/<str:order_number>/return/", views.order_return_request, name="order_return_request"),
    path("order/<str:order_number>/return/initiate/", views.order_return_quick, name="order_return_quick"),
]
