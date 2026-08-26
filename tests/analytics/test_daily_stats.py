from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.services import record_daily_stats
from apps.giveaway.services import MOSCOW_TZ
from apps.promocodes.models import PromoRedemptionAttempt


def test_record_daily_stats_counts_registrations_and_attempts(db) -> None:
    """Статистика за день считает новых пользователей и попытки погашения."""
    User.objects.create_user(email="a@example.com", password="x")
    User.objects.create_user(email="b@example.com", password="x")
    user = User.objects.create_user(email="c@example.com", password="x")
    PromoRedemptionAttempt.objects.create(
        user=user, code_input="AAAA1111", success=True
    )
    PromoRedemptionAttempt.objects.create(
        user=user,
        code_input="BBBB2222",
        success=False,
        failure_reason="not_found",
    )

    today = timezone.now().astimezone(MOSCOW_TZ).date()
    stats = record_daily_stats(today)

    assert stats.users_registered == 3
    assert stats.promo_success == 1
    assert stats.promo_failed == 1
