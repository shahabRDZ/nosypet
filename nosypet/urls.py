from django.contrib import admin
from django.urls import include, path

from pets import views as pets_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),
    # PWA: must be served at root so the SW scope covers the whole site.
    path("manifest.webmanifest", pets_views.manifest, name="manifest"),
    path("sw.js", pets_views.service_worker, name="service_worker"),
    path("", include("pets.urls")),
]
