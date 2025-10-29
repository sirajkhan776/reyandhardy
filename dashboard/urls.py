from django.urls import path
from . import views


urlpatterns = [
    path("dashboard/", views.index, name="dashboard"),
    path("dashboard/categories/new/", views.create_category, name="dashboard_category_new"),
    path("dashboard/products/new/", views.create_product, name="dashboard_product_new"),
    path("dashboard/banners/new/", views.create_banner, name="dashboard_banner_new"),
    path("dashboard/orders/new/", views.create_order, name="dashboard_order_new"),
]
