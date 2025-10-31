from django.urls import path
from . import views


urlpatterns = [
    path("profile/", views.profile, name="profile"),
    path("delivery/set/", views.delivery_set, name="delivery_set"),
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/clear/", views.notifications_clear, name="notifications_clear"),
    path("you/", views.you, name="you"),
    path("help/", views.help_center, name="help_center"),
    path("addresses/", views.addresses, name="addresses"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("addresses/<int:pk>/default/", views.address_make_default, name="address_make_default"),
    # Security actions
    path("security/signout-all/", views.signout_all_sessions, name="signout_all_sessions"),
    path("security/delete/", views.delete_account, name="delete_account"),
]
