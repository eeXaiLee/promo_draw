from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.accounts.models import User

from .forms import PromoCodeForm
from .services import redeem_code


class RedeemCodeView(LoginRequiredMixin, FormView):
    """Страница ввода промокода — доступна только с заполненным профилем."""

    form_class = PromoCodeForm
    template_name = "promocodes/redeem_code.html"
    success_url = reverse_lazy("promocodes:redeem")

    def _profile_incomplete_redirect(self) -> HttpResponse | None:
        user = self.request.user
        assert isinstance(user, User)
        if user.profile_is_complete:
            return None
        messages.error(
            self.request,
            "Чтобы ввести промокод, сначала заполните профиль.",
        )
        return redirect("accounts:profile")

    def get(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        redirect_response = self._profile_incomplete_redirect()
        if redirect_response is not None:
            return redirect_response
        return super().get(request, *args, **kwargs)

    def post(
        self, request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        redirect_response = self._profile_incomplete_redirect()
        if redirect_response is not None:
            return redirect_response
        return super().post(request, *args, **kwargs)

    def form_valid(self, form: PromoCodeForm) -> HttpResponse:
        user = self.request.user
        assert isinstance(user, User)
        result = redeem_code(user, form.cleaned_data["code"])
        if result.success:
            messages.success(self.request, result.message)
        else:
            messages.error(self.request, result.message)
        return super().form_valid(form)
