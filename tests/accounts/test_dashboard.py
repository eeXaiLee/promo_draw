from __future__ import annotations

from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.promocodes.models import PromoCode


def test_dashboard_shows_promo_code_form(
    client: Client, complete_user: User
) -> None:
    """Личный кабинет вошедшего пользователя содержит форму ввода кода."""
    client.force_login(complete_user)

    response = client.get(reverse("accounts:dashboard"))

    assert response.status_code == 200


def test_dashboard_accepts_valid_code(
    client: Client, complete_user: User
) -> None:
    """Правильный код принимается прямо на дашборде."""
    PromoCode.objects.create(code="GOOD0001")
    client.force_login(complete_user)

    response = client.post(
        reverse("accounts:dashboard"), {"code": "GOOD0001"}, follow=True
    )

    assert "Промокод принят" in response.content.decode()


def test_dashboard_rejects_unknown_code(
    client: Client, complete_user: User
) -> None:
    """Неверный код отклоняется с понятным сообщением, а не ошибкой сервера."""
    client.force_login(complete_user)

    response = client.post(
        reverse("accounts:dashboard"), {"code": "NOPE0000"}, follow=True
    )

    assert response.status_code == 200
    assert "не найден" in response.content.decode()
