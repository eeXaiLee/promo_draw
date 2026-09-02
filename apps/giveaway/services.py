from __future__ import annotations

import datetime
import secrets
from zoneinfo import ZoneInfo

from django.db import transaction

from apps.accounts.models import User
from apps.promocodes.models import PromoCode

from .models import DrawKind, MonthlyDraw, Prize, Winner

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def moscow_day_bounds(
    day: datetime.date,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Границы календарных суток `day` по московскому времени."""
    start = datetime.datetime.combine(day, datetime.time.min, MOSCOW_TZ)
    return start, start + datetime.timedelta(days=1)


def moscow_period_bounds(
    period_start: datetime.date, period_end: datetime.date
) -> tuple[datetime.datetime, datetime.datetime]:
    """Границы периода `period_start`..`period_end` (включительно) по МСК."""
    start, _ = moscow_day_bounds(period_start)
    _, end = moscow_day_bounds(period_end)
    return start, end


def finalize_draw(
    draw: MonthlyDraw, determined_by: User | None = None
) -> list[Winner]:
    """Определяет победителей розыгрыша.

    Если розыгрыш уже финализирован, ничего не делает.
    Так ручной запуск из админки и автоматическая задача не мешают друг другу.

    Каждый погашенный за период код — отдельный билет: чем больше кодов
    погасил человек, тем выше его шанс выиграть.

    Победа в одном виде розыгрыша (`kind`) не исключает участие в другом —
    например, победитель ежемесячного всё равно участвует в супер-розыгрыше.

    `determined_by` — сотрудник, запустивший розыгрыш вручную из админки.
    Для автоматического запуска остаётся None.
    """
    from .tasks import send_winner_email

    with transaction.atomic():
        draw = MonthlyDraw.objects.select_for_update().get(pk=draw.pk)
        if draw.is_finalized:
            return []

        period_start, period_end = moscow_period_bounds(
            draw.period_start, draw.period_end
        )
        tickets = list(
            PromoCode.objects.filter(
                used_by__isnull=False,
                used_at__gte=period_start,
                used_at__lt=period_end,
            ).exclude(used_by__giveaway_wins__kind=draw.kind)
        )
        secrets.SystemRandom().shuffle(tickets)

        prizes = list(Prize.objects.filter(is_active=True, kind=draw.kind))
        secrets.SystemRandom().shuffle(prizes)

        max_winners = min(draw.prize_count, len(prizes))
        seen_users: set[int] = set()
        winners: list[Winner] = []
        for promo_code in tickets:
            if len(winners) >= max_winners:
                break
            user_id = promo_code.used_by_id
            assert user_id is not None
            if user_id in seen_users:
                continue
            seen_users.add(user_id)
            winners.append(
                Winner.objects.create(
                    draw=draw,
                    prize=prizes[len(winners)],
                    user_id=user_id,
                    kind=draw.kind,
                    promo_code=promo_code,
                    determined_manually=determined_by is not None,
                    determined_by=determined_by,
                )
            )

        draw.is_finalized = True
        draw.save(update_fields=["is_finalized"])

    for winner in winners:
        send_winner_email.delay(winner.pk)

    return winners


def next_monthly_period(
    today: datetime.date,
) -> tuple[datetime.date, datetime.date]:
    """Период очередного ежемесячного розыгрыша: с 10-го числа прошлого
    месяца по 9-е текущего (включительно) — вызывается 10-го числа, когда
    предыдущий период уже полностью закрыт."""
    period_end = today - datetime.timedelta(days=1)
    if today.month == 1:
        prev_month, prev_year = 12, today.year - 1
    else:
        prev_month, prev_year = today.month - 1, today.year
    period_start = datetime.date(prev_year, prev_month, 10)
    return period_start, period_end


def get_or_create_monthly_draw(today: datetime.date) -> MonthlyDraw:
    """Розыгрыш за только что закрывшийся месячный период."""
    period_start, period_end = next_monthly_period(today)
    draw, _ = MonthlyDraw.objects.get_or_create(
        period_start=period_start,
        period_end=period_end,
        kind=DrawKind.MONTHLY,
        defaults={"prize_count": 2},
    )
    return draw
