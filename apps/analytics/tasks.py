from __future__ import annotations

import datetime

from celery import shared_task
from django.utils import timezone

from apps.giveaway.services import MOSCOW_TZ

from .services import record_daily_stats


@shared_task
def record_yesterday_stats() -> None:
    """Считает и сохраняет статистику за прошедшие сутки по МСК."""
    today_msk = timezone.now().astimezone(MOSCOW_TZ).date()
    yesterday = today_msk - datetime.timedelta(days=1)
    record_daily_stats(yesterday)
