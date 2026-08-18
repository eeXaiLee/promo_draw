from __future__ import annotations

import datetime

from celery import shared_task
from django.utils import timezone

from .models import DailyDraw
from .services import MOSCOW_TZ, finalize_draw


@shared_task
def finalize_yesterday_draw() -> None:
    """Финализирует розыгрыш за только что закончившиеся сутки по МСК."""
    today_msk = timezone.now().astimezone(MOSCOW_TZ).date()
    yesterday = today_msk - datetime.timedelta(days=1)
    draw, _ = DailyDraw.objects.get_or_create(date=yesterday)
    finalize_draw(draw)
