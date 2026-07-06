from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


def home_view(request):
    if request.user.is_authenticated:
        return redirect("app:dashboard")
    return render(request, "marketing/home.html")

def pricing_view(request):
    return render(request, "marketing/pricing.html")