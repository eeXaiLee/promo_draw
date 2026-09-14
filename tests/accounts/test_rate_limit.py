from __future__ import annotations

from django.core import mail
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.accounts import rate_limit
from apps.accounts.forms import PasswordResetRequestForm
from apps.accounts.models import User
from apps.accounts.rate_limit import LOGIN_FAILS_THRESHOLD


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


def test_resend_confirmation_email_rate_limited(
    complete_user: User, client: Client
) -> None:
    """Повторная отправка письма подтверждения чаще раза в минуту
    отклоняется — иначе можно засыпать себя письмами по кругу."""
    complete_user.email_confirmed = False
    complete_user.save(update_fields=["email_confirmed"])
    client.force_login(complete_user)

    client.post(reverse("accounts:resend_confirmation_email"))
    response = client.post(
        reverse("accounts:resend_confirmation_email"), follow=True
    )

    assert "Подождите минуту" in response.content.decode()


def test_login_locks_after_repeated_failures(
    complete_user: User, client: Client
) -> None:
    """После порога неверных попыток не пускает даже с верным паролем."""
    for _ in range(LOGIN_FAILS_THRESHOLD):
        client.post(
            reverse("accounts:login"),
            {"username": complete_user.email, "password": "wrong"},
        )

    response = client.post(
        reverse("accounts:login"),
        {"username": complete_user.email, "password": "testpass123"},
    )

    assert response.status_code == 200
    assert "Слишком много неверных попыток входа" in response.content.decode()


def test_register_failed_login_lockout_grows_with_more_failures() -> None:
    """Прогрессивная задержка — каждая попытка сверх порога удлиняет бан."""
    email, ip = "u@example.com", "1.2.3.4"
    for _ in range(LOGIN_FAILS_THRESHOLD):
        rate_limit.register_failed_login(email, ip)
    first_unlock = rate_limit.cache.get(rate_limit._lock_key(email, ip))

    rate_limit.register_failed_login(email, ip)
    second_unlock = rate_limit.cache.get(rate_limit._lock_key(email, ip))

    assert second_unlock > first_unlock


def test_clear_failed_logins_removes_lock() -> None:
    """Успешный вход должен снимать блокировку, а не ждать её истечения."""
    email, ip = "u@example.com", "1.2.3.4"
    for _ in range(LOGIN_FAILS_THRESHOLD):
        rate_limit.register_failed_login(email, ip)
    assert rate_limit.get_login_lock_message(email, ip) is not None

    rate_limit.clear_failed_logins(email, ip)

    assert rate_limit.get_login_lock_message(email, ip) is None
