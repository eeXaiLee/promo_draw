from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("promo/", include("apps.promocodes.urls")),
    path("winners/", include("apps.giveaway.urls")),
]
