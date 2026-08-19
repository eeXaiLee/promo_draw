from __future__ import annotations

import datetime

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.analytics.services import record_daily_stats

from .models import DailyDraw, Winner
from .services import MOSCOW_TZ, finalize_draw


@shared_task
def finalize_yesterday_draw() -> None:
    """Финализирует розыгрыш и считает статистику за прошедшие сутки по МСК."""
    today_msk = timezone.now().astimezone(MOSCOW_TZ).date()
    yesterday = today_msk - datetime.timedelta(days=1)
    draw, _ = DailyDraw.objects.get_or_create(date=yesterday)
    finalize_draw(draw)
    record_daily_stats(yesterday)


@shared_task
def send_winner_email(winner_id: int) -> None:
    """Письмо победителю — обязательное, без возможности отключить."""
    try:
        winner = Winner.objects.select_related("user", "prize").get(
            pk=winner_id
        )
    except Winner.DoesNotExist:
        return

    body = render_to_string(
        "giveaway/emails/winner.txt", {"prize": winner.prize.title}
    )
    send_mail(
        subject="Вы выиграли! — promo_draw",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[winner.user.email],
    )
