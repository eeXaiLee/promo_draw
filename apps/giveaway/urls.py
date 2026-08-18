from django.urls import path

from . import views

app_name = "giveaway"

urlpatterns = [
    path("", views.winners_page, name="winners"),
]
