from __future__ import annotations

from django.test import Client
from django.urls import reverse

from apps.accounts.models import User


def test_winners_page_redirects_anonymous_to_login(client: Client) -> None:
    """Без входа страница победителей недоступна — редирект на логин."""
    response = client.get(reverse("giveaway:winners"))

    assert response.status_code == 302
    assert response["Location"].startswith(reverse("accounts:login"))


def test_winners_page_opens_for_logged_in_user(
    client: Client, complete_user: User
) -> None:
    """Вошедшему пользователю страница победителей открывается."""
    client.force_login(complete_user)

    response = client.get(reverse("giveaway:winners"))

    assert response.status_code == 200
