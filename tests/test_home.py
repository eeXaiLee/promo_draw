from __future__ import annotations

from django.test import Client
from django.urls import reverse

from promo_draw.views import FAQ_ITEMS


def test_home_page_renders_faq_from_shared_data(
    client: Client, db: None
) -> None:
    """Главная берёт вопросы из общего списка FAQ_ITEMS, а не хардкодит
    текст в шаблоне — иначе снова разъедется с кабинетом."""
    response = client.get(reverse("home"))
    content = response.content.decode()

    assert "Частые вопросы" in content
    assert FAQ_ITEMS[0]["question"] in content
    assert FAQ_ITEMS[0]["answer"] in content
