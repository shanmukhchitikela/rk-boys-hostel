"""URL configuration for the config project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("rooms/", include("rooms.urls")),
    path("residents/", include("residents.urls")),
    path("billing/", include("billing.urls")),
    path("reports/", include("reports.urls")),
    path("workspace/", include("auditlog.urls")),
    path("", include("core.urls")),
]