from django.urls import path
from marketing.views.pages import home_view, pricing_view


app_name = "marketing"

urlpatterns = [
    path("", home_view, name="home"),
    path("pricing/", pricing_view, name="pricing"),
    #path("contact/", contact_view, name="contact"),
]