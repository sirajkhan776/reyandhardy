from django.urls import path
from . import views


urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("you/", views.you, name="you"),
    path("help/", views.help_center, name="help_center"),
    path("addresses/", views.addresses, name="addresses"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("addresses/<int:pk>/default/", views.address_make_default, name="address_make_default"),
]
