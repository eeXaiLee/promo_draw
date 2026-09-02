from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("promo/", include("apps.promocodes.urls")),
    path("winners/", include("apps.giveaway.urls")),
    path("about/", views.stub_view("about"), name="about"),
    path("contacts/", views.stub_view("contacts"), name="contacts"),
    path("promotions/", views.stub_view("promotions"), name="promotions"),
    path(
        "personal-data/",
        views.stub_view("personal-data"),
        name="personal-data",
    ),
    path(
        "user-agreement/",
        views.stub_view("user-agreement"),
        name="user-agreement",
    ),
    path(
        "loyalty-rules/",
        views.stub_view("loyalty-rules"),
        name="loyalty-rules",
    ),
    path(
        "loyalty-terms/",
        views.stub_view("loyalty-terms"),
        name="loyalty-terms",
    ),
    path("organizer/", views.stub_view("organizer"), name="organizer"),
    path(
        "cookie-policy/",
        views.stub_view("cookie-policy"),
        name="cookie-policy",
    ),
]
