from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home_view(request):
    return render(request, "marketing/home.html")

def pricing_view(request):
    return render(request, "marketing/pricing.html")