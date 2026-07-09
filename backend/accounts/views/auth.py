from django.contrib import messages
from django.contrib.auth import login, logout
from django.db import IntegrityError
from django.shortcuts import redirect, render

from accounts.forms import LoginForm, SignupForm
from accounts.services.company_switch import set_active_company
from accounts.services.signup import register_owner


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("app:dashboard")

    form = SignupForm()

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                user, company, membership = register_owner(
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    company_name=form.cleaned_data["company_name"],
                )
                login(request, user)
                request.session["active_company_id"] = str(company.id)
                messages.success(request, "Welcome to CrewLution!")
                return redirect("app:dashboard")
            except ValueError as exc:
                messages.error(request, str(exc))
            except IntegrityError:
                messages.error(request, "An account with this email already exists.")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(request, "accounts/signup.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("app:dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Set the active company to the first active membership
            membership = user.company_memberships.filter(is_active=True).select_related("company").first()
            if membership:
                set_active_company(request=request, company_id=membership.company.id)
            messages.success(request, "Logged in successfully.")
            return redirect("app:dashboard")
        else:
            messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("accounts:login")