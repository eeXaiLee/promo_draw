from __future__ import annotations

import datetime

import pytest
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User
from apps.giveaway.models import Prize
from promo_draw.celery import app as celery_app


@pytest.fixture
def client() -> Client:
    """Возвращает тестовый HTTP-клиент с подменой заголовка `X-Forwarded-Proto`.

    Используется для эмуляции запросов, приходящих через HTTPS,
    как в боевой среде.
    """
    return Client(HTTP_X_FORWARDED_PROTO="https")


@pytest.fixture(autouse=True)
def _eager_celery(settings):
    """Таски выполняются синхронно — тестам не нужен настоящий брокер/воркер."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def _clear_cache():
    """Бан и счётчик неудачных попыток живут в общем Redis — изолируем тесты."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def complete_user(db) -> User:
    """Пользователь с заполненным профилем и подтверждённой почтой.

    Может гасить промокоды.
    """
    return User.objects.create_user(
        email="redeemer@example.com",
        password="testpass123",
        first_name="Иван",
        last_name="Иванов",
        birth_date=datetime.date(1990, 1, 1),
        phone="+79991234567",
        email_confirmed=True,
    )


@pytest.fixture
def profile_form_data() -> dict[str, object]:
    """Валидные данные для ProfileForm — телефон намеренно в сыром виде."""
    return {
        "last_name": "Иванов",
        "first_name": "Иван",
        "birth_date": "1990-01-01",
        "phone": "8 (999) 123-45-67",
        "notify_promo_registered": True,
    }


@pytest.fixture
def two_prizes(db) -> list[Prize]:
    """Два активных приза — под `DRAW_PRIZE_COUNT` из giveaway."""
    return [
        Prize.objects.create(title="Сертификат"),
        Prize.objects.create(title="Наушники"),
    ]
