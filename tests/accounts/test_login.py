from __future__ import annotations

from django.test import Client
from django.urls import reverse

from apps.accounts.models import User


def _login(client: Client, user: User, *, remember_me: bool) -> None:
    data = {"username": user.email, "password": "testpass123"}
    if remember_me:
        data["remember_me"] = "on"
    client.post(reverse("accounts:login"), data)


def test_remember_me_checked_keeps_persistent_session(
    client: Client, complete_user: User
) -> None:
    """С галочкой сессия переживает закрытие браузера (обычное поведение)."""
    _login(client, complete_user, remember_me=True)

    assert client.session.get_expire_at_browser_close() is False


def test_remember_me_unchecked_expires_session_on_browser_close(
    client: Client, complete_user: User
) -> None:
    """Без галочки сессия обнуляется при закрытии браузера."""
    _login(client, complete_user, remember_me=False)

    assert client.session.get_expire_at_browser_close() is True


def test_logged_in_user_is_redirected_away_from_login_page(
    client: Client, complete_user: User
) -> None:
    """Вошедшему незачем видеть форму входа — сразу в кабинет."""
    client.force_login(complete_user)

    response = client.get(reverse("accounts:login"))

    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:dashboard")


def test_logged_in_user_is_redirected_away_from_register_page(
    client: Client, complete_user: User
) -> None:
    """Вошедшему незачем видеть форму регистрации — сразу в кабинет."""
    client.force_login(complete_user)

    response = client.get(reverse("accounts:register"))

    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:dashboard")
