from __future__ import annotations

from django.core import mail
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.accounts.forms import PasswordResetRequestForm
from apps.accounts.models import User


def test_password_reset_repeat_request_is_not_sent_twice(
    complete_user: User,
) -> None:
    """Повторный запрос сброса на тот же адрес не шлёт письмо второй раз."""
    request = RequestFactory().post("/accounts/reset-password/")

    first_form = PasswordResetRequestForm(data={"email": complete_user.email})
    assert first_form.is_valid()
    first_form.save(request=request)

    second_form = PasswordResetRequestForm(data={"email": complete_user.email})
    assert second_form.is_valid()
    second_form.save(request=request)

    assert len(mail.outbox) == 1


def test_registration_repeat_request_from_same_ip_is_rejected(
    client: Client, db: None
) -> None:
    """Вторую регистрацию с того же IP в течение минуты форма отклоняет."""

    def _register(email: str) -> None:
        client.post(
            reverse("accounts:register"),
            {
                "email": email,
                "password1": "Zx9!brQpLk3Wmbfr82",
                "password2": "Zx9!brQpLk3Wmbfr82",
                "personal_data_consent": "on",
            },
        )

    _register("first@example.com")
    assert User.objects.filter(email="first@example.com").exists()

    _register("second@example.com")

    assert not User.objects.filter(email="second@example.com").exists()
