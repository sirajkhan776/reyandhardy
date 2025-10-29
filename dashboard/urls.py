from django.urls import path
from . import views


urlpatterns = [
    path("dashboard/", views.index, name="dashboard"),
    path("dashboard/orders/", views.orders_list, name="dashboard_orders"),
    path("dashboard/products/", views.products_list, name="dashboard_products"),
    path("dashboard/categories/", views.categories_list, name="dashboard_categories"),
    path("dashboard/banners/", views.banners_list, name="dashboard_banners"),
    path("dashboard/categories/new/", views.create_category, name="dashboard_category_new"),
    path("dashboard/products/new/", views.create_product, name="dashboard_product_new"),
    path("dashboard/banners/new/", views.create_banner, name="dashboard_banner_new"),
    path("dashboard/orders/new/", views.create_order, name="dashboard_order_new"),
    path("dashboard/orders/<int:pk>/status/", views.update_order_status, name="dashboard_order_status"),
    # Edit
    path("dashboard/products/<int:pk>/edit/", views.edit_product, name="dashboard_product_edit"),
    path("dashboard/categories/<int:pk>/edit/", views.edit_category, name="dashboard_category_edit"),
    path("dashboard/banners/<int:pk>/edit/", views.edit_banner, name="dashboard_banner_edit"),
    path("dashboard/orders/<int:pk>/edit/", views.edit_order, name="dashboard_order_edit"),
    # Delete
    path("dashboard/products/<int:pk>/delete/", views.delete_product, name="dashboard_product_delete"),
    path("dashboard/categories/<int:pk>/delete/", views.delete_category, name="dashboard_category_delete"),
    path("dashboard/banners/<int:pk>/delete/", views.delete_banner, name="dashboard_banner_delete"),
    path("dashboard/orders/<int:pk>/delete/", views.delete_order, name="dashboard_order_delete"),
]
