from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import RegistrationForm


class RegisterView(CreateView):
    """Регистрация: создаёт пользователя, дальше — подтверждение почты."""

    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:register_done")


def register_done(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/register_done.html")
