"""
config/urls.py is the top-level entry.
It delegates /app/ to app_urls.py so public and private routes stay separate.
Essentially, public site vs authenticated app.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path("", include("marketing.urls", namespace="marketing")),
    path("app/", include("config.app_urls")),
    path("accounts/", include("accounts.urls", namespace="accounts")),
]
