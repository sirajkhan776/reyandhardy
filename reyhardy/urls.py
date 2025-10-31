from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("allauth.urls")),
    path("", include("catalog.urls")),
    path("", include("cart.urls")),
    path("", include("orders.urls")),
    path("", include("payments.urls")),
    path("", include("dashboard.urls")),
    path("", include("reviews.urls")),
]

# Serve media files from Django. In production you should use a proper
# web server or object storage, but this keeps Render/simple deploys working.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
