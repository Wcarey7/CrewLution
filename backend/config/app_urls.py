"""
URL router for the authenticated product — everything under /app/.
app_urls.py is the front door to the logged-in CrewLution app at /app/, 
kept separate from marketing and auth so the URL structure stays clean
"""
from django.urls import path
from commerce.views.dashboard import dashboard_view

app_name = "app"

urlpatterns = [
    path("", dashboard_view, name="dashboard"),
]
