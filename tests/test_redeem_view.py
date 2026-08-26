from __future__ import annotations

from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.promocodes.models import PromoCode


def test_redeem_page_shows_form_for_logged_in_user(
    client: Client, complete_user: User
) -> None:
    """Вошедший пользователь с заполненным профилем видит страницу с формой."""
    client.force_login(complete_user)

    response = client.get(reverse("promocodes:redeem"))

    assert response.status_code == 200


def test_redeem_page_accepts_valid_code(
    client: Client, complete_user: User
) -> None:
    """Правильный код через страницу принимается — видно сообщение об успехе."""
    PromoCode.objects.create(code="GOOD0001")
    client.force_login(complete_user)

    response = client.post(
        reverse("promocodes:redeem"), {"code": "GOOD0001"}, follow=True
    )

    assert "Промокод принят" in response.content.decode()


def test_redeem_page_rejects_unknown_code(
    client: Client, complete_user: User
) -> None:
    """Неверный код отклоняется с понятным сообщением, а не ошибкой сервера."""
    client.force_login(complete_user)

    response = client.post(
        reverse("promocodes:redeem"), {"code": "NOPE0000"}, follow=True
    )

    assert response.status_code == 200
    assert "не найден" in response.content.decode()
