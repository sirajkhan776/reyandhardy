from django.urls import path
from . import views


urlpatterns = [
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_cart_item, name="remove_cart_item"),
    path("cart/save/<int:item_id>/", views.save_for_later, name="save_for_later"),
    path("cart/checkout/selected/", views.checkout_selected, name="checkout_selected"),
    path("cart/move/<int:product_id>/", views.move_saved_to_cart, name="move_saved_to_cart"),
    path("cart/coupon/apply/", views.apply_coupon, name="apply_coupon"),
    path("cart/coupon/remove/", views.remove_coupon, name="remove_coupon"),
]
