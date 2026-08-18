from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("promo/", include("apps.promocodes.urls")),
    path("winners/", include("apps.giveaway.urls")),
]
