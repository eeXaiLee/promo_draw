from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView

from apps.promocodes.forms import PromoCodeForm
from apps.promocodes.services import redeem_code

from .forms import ProfileForm, RegistrationForm
from .models import User
from .rate_limit import get_client_ip, hit_rate_limit
from .tasks import send_confirmation_email
from .tokens import email_confirmation_token


class RegisterView(CreateView):
    """Регистрация: создаёт пользователя, дальше — подтверждение почты."""

    form_class = RegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:register_done")

    def form_valid(self, form: RegistrationForm) -> HttpResponse:
        email = form.cleaned_data["email"]
        rate_limited = hit_rate_limit(
            f"register:ip:{get_client_ip(self.request)}"
        )
        rate_limited = hit_rate_limit(f"register:email:{email}") or rate_limited
        if rate_limited:
            form.add_error(
                None,
                "Слишком много попыток регистрации. Подождите минуту и "
                "попробуйте снова.",
            )
            return self.form_invalid(form)

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


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    """Личный кабинет — сюда же встроен ввод промокода."""
    user = request.user
    assert isinstance(user, User)

    form = PromoCodeForm()
    if request.method == "POST":
        form = PromoCodeForm(request.POST)
        if form.is_valid():
            result = redeem_code(user, form.cleaned_data["code"])
            if result.success:
                messages.success(request, result.message)
            else:
                messages.error(request, result.message)
            return redirect("accounts:dashboard")

    return render(request, "accounts/dashboard.html", {"form": form})


@login_required
@require_POST
def resend_confirmation_email(request: HttpRequest) -> HttpResponse:
    """Повторно отправляет письмо подтверждения почты."""
    user = request.user
    assert isinstance(user, User)
    if user.email_confirmed:
        messages.info(request, "Почта уже подтверждена.")
    else:
        send_confirmation_email.delay(user.pk)
        messages.success(request, "Письмо с подтверждением отправлено.")
    return redirect("accounts:dashboard")


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Личные данные пользователя — обязательны для ввода промокода."""

    model = User
    form_class = ProfileForm
    template_name = "accounts/profile_form.html"
    success_url = reverse_lazy("accounts:dashboard")

    def get_object(self, queryset: QuerySet[User] | None = None) -> User:
        assert isinstance(self.request.user, User)
        return self.request.user

    def form_valid(self, form: ProfileForm) -> HttpResponse:
        messages.success(self.request, "Профиль сохранён.")
        return super().form_valid(form)
