from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard_view(request):
  return render(request, "common/dashboard.html")

app_name = "app"
urlpatterns = [
  path("", dashboard_view, name="dashboard"),
]