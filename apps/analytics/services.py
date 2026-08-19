from __future__ import annotations

import datetime

from apps.accounts.models import User
from apps.giveaway.services import moscow_day_bounds
from apps.promocodes.models import PromoRedemptionAttempt

from .models import DailyStats


def record_daily_stats(day: datetime.date) -> DailyStats:
    """Считает и сохраняет статистику за календарные сутки по МСК."""
    day_start, day_end = moscow_day_bounds(day)

    users_registered = User.objects.filter(
        date_joined__gte=day_start, date_joined__lt=day_end
    ).count()

    attempts = PromoRedemptionAttempt.objects.filter(
        created_at__gte=day_start, created_at__lt=day_end
    )
    promo_success = attempts.filter(success=True).count()
    promo_failed = attempts.filter(success=False).count()

    stats, _ = DailyStats.objects.update_or_create(
        date=day,
        defaults={
            "users_registered": users_registered,
            "promo_success": promo_success,
            "promo_failed": promo_failed,
        },
    )
    return stats
