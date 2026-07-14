"""
config/urls.py is the top-level entry.
It delegates /app/ to app_urls.py so public and private routes stay separate.
Essentially, public site vs authenticated app.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Path comes from DJANGO_ADMIN_URL in .env (not the predictable /admin/).
    path(settings.ADMIN_URL, admin.site.urls),

    path("", include("marketing.urls", namespace="marketing")),
    path("app/", include("config.app_urls")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
]
