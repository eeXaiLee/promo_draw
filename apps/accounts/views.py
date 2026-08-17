from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.generic import CreateView

from .forms import RegistrationForm
from .models import User
from .tasks import send_confirmation_email
from .tokens import email_confirmation_token


class RegisterView(CreateView):
    """Регистрация: создаёт пользователя, дальше — подтверждение почты."""

    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:register_done")

    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        response = super().form_valid(form)
        assert self.object is not None
        send_confirmation_email.delay(self.object.pk)
        return response


def register_done(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/register_done.html")


def confirm_email(
    request: HttpRequest, uidb64: str, token: str
) -> HttpResponse:
    """Подтверждает почту по ссылке из письма."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_confirmation_token.check_token(user, token):
        user.email_confirmed = True
        user.save(update_fields=["email_confirmed"])
        confirmed = True
    else:
        confirmed = False

    return render(
        request,
        "accounts/confirm_email_result.html",
        {"confirmed": confirmed},
    )
