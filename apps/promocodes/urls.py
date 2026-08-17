from django.urls import path

from . import views

app_name = "promocodes"

urlpatterns = [
    path("", views.RedeemCodeView.as_view(), name="redeem"),
]
