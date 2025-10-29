from django.urls import path
from . import views


urlpatterns = [
    path("dashboard/", views.index, name="dashboard"),
    path("dashboard/analytics.json", views.analytics_data, name="dashboard_analytics_data"),
    path("dashboard/analytics.csv", views.analytics_csv, name="dashboard_analytics_csv"),
    path("dashboard/orders/", views.orders_list, name="dashboard_orders"),
    path("dashboard/orders/partial/", views.orders_partial, name="dashboard_orders_partial"),
    path("dashboard/orders/<int:pk>/", views.order_detail_admin, name="dashboard_order_detail"),
    path("dashboard/products/", views.products_list, name="dashboard_products"),
    path("dashboard/products/partial/", views.products_partial, name="dashboard_products_partial"),
    path("dashboard/categories/", views.categories_list, name="dashboard_categories"),
    path("dashboard/categories/partial/", views.categories_partial, name="dashboard_categories_partial"),
    path("dashboard/banners/", views.banners_list, name="dashboard_banners"),
    path("dashboard/banners/partial/", views.banners_partial, name="dashboard_banners_partial"),
    path("dashboard/coupons/", views.coupons_list, name="dashboard_coupons"),
    path("dashboard/coupons/partial/", views.coupons_partial, name="dashboard_coupons_partial"),
    path("dashboard/users/", views.users_list, name="dashboard_users"),
    path("dashboard/users/partial/", views.users_partial, name="dashboard_users_partial"),
    path("dashboard/users/<int:pk>/", views.user_detail_admin, name="dashboard_user_detail"),
    path("dashboard/users/<int:pk>/staff/", views.toggle_user_staff, name="dashboard_user_toggle_staff"),
    path("dashboard/users/<int:pk>/active/", views.toggle_user_active, name="dashboard_user_toggle_active"),
    path("dashboard/users.csv", views.users_csv, name="dashboard_users_csv"),
    path("dashboard/categories/new/", views.create_category, name="dashboard_category_new"),
    path("dashboard/products/new/", views.create_product, name="dashboard_product_new"),
    path("dashboard/banners/new/", views.create_banner, name="dashboard_banner_new"),
    path("dashboard/orders/new/", views.create_order, name="dashboard_order_new"),
    path("dashboard/coupons/new/", views.create_coupon, name="dashboard_coupon_new"),
    path("dashboard/orders/<int:pk>/status/", views.update_order_status, name="dashboard_order_status"),
    # Edit
    path("dashboard/products/<int:pk>/edit/", views.edit_product, name="dashboard_product_edit"),
    path("dashboard/categories/<int:pk>/edit/", views.edit_category, name="dashboard_category_edit"),
    path("dashboard/banners/<int:pk>/edit/", views.edit_banner, name="dashboard_banner_edit"),
    path("dashboard/orders/<int:pk>/edit/", views.edit_order, name="dashboard_order_edit"),
    path("dashboard/coupons/<int:pk>/edit/", views.edit_coupon, name="dashboard_coupon_edit"),
    # Delete
    path("dashboard/products/<int:pk>/delete/", views.delete_product, name="dashboard_product_delete"),
    path("dashboard/categories/<int:pk>/delete/", views.delete_category, name="dashboard_category_delete"),
    path("dashboard/banners/<int:pk>/delete/", views.delete_banner, name="dashboard_banner_delete"),
    path("dashboard/orders/<int:pk>/delete/", views.delete_order, name="dashboard_order_delete"),
    path("dashboard/coupons/<int:pk>/delete/", views.delete_coupon, name="dashboard_coupon_delete"),
]
