from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from promo_draw.celery import EMAIL_TASK_KWARGS

from . import promo_period
from .models import Winner
from .services import (
    MOSCOW_TZ,
    finalize_draw,
    get_or_create_monthly_draw,
    get_or_create_monthly_draw_for_period,
    get_or_create_super_draw,
)


@shared_task
def finalize_monthly_draw() -> None:
    """Финализирует ежемесячный розыгрыш, назначенный на сегодня.

    Запускается 9-го числа в 21:00 МСК. Если сегодня не день розыгрыша
    (расписание Celery Beat сработало не вовремя) — ничего не делает,
    оставляя это `catch_up_monthly_draws`.
    """
    today_msk = timezone.now().astimezone(MOSCOW_TZ).date()
    draw = get_or_create_monthly_draw(today_msk)
    if draw is not None:
        finalize_draw(draw)


@shared_task
def catch_up_monthly_draws() -> None:
    """Подстраховка на случай простоя ровно в момент розыгрыша.

    Раз в 30 минут проверяет все периоды акции, чей день розыгрыша уже
    наступил, и дозакрывает те, что почему-то остались не финализированы.
    """
    today_msk = timezone.now().astimezone(MOSCOW_TZ).date()
    for period_start, period_end in promo_period.monthly_periods():
        if period_end > today_msk:
            continue
        draw = get_or_create_monthly_draw_for_period(period_start, period_end)
        if not draw.is_finalized:
            finalize_draw(draw)

    if today_msk > promo_period.CAMPAIGN_END.date():
        super_draw = get_or_create_super_draw()
        if not super_draw.is_finalized:
            finalize_draw(super_draw)


@shared_task
def finalize_super_draw() -> None:
    """Финализирует супер-розыгрыш — разовое событие в конце акции."""
    draw = get_or_create_super_draw()
    finalize_draw(draw)


@shared_task(**EMAIL_TASK_KWARGS)
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
    winner.email_sent_at = timezone.now()
    winner.save(update_fields=["email_sent_at"])


@shared_task
def resend_pending_winner_emails() -> None:
    """Досылает письма победителям, которым оно ещё не ушло."""
    pending_ids = Winner.objects.filter(email_sent_at__isnull=True)
    for winner_id in pending_ids.values_list("pk", flat=True):
        send_winner_email.delay(winner_id)
