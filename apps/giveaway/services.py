from __future__ import annotations

import datetime
import secrets
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.db import transaction
from django.template.defaultfilters import date as format_date

from apps.accounts.models import User
from apps.promocodes.models import PromoCode

from . import promo_period
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


def get_or_create_monthly_draw_for_period(
    period_start: datetime.date, period_end: datetime.date
) -> MonthlyDraw:
    """Розыгрыш за конкретный месячный период (создаёт, если ещё нет)."""
    draw, _ = MonthlyDraw.objects.get_or_create(
        period_start=period_start,
        period_end=period_end,
        kind=DrawKind.MONTHLY,
        defaults={"prize_count": 2},
    )
    return draw


def get_or_create_monthly_draw(today: datetime.date) -> MonthlyDraw | None:
    """Розыгрыш за период, чей день розыгрыша — сегодня.

    `None`, если сегодня не 9-е число одного из месяцев акции (март–декабрь) —
    так автозадача остаётся безопасной, даже если расписание Celery Beat
    почему-то сработает вне графика акции.
    """
    period = promo_period.monthly_period_ending_on(today)
    if period is None:
        return None
    return get_or_create_monthly_draw_for_period(*period)


SUPER_DRAW_PRIZE_COUNT = 4


def get_or_create_super_draw() -> MonthlyDraw:
    """Супер-розыгрыш — разовое событие в конце акции, билеты за весь
    срок акции, без исключения прошлых победителей ежемесячных розыгрышей."""
    draw, _ = MonthlyDraw.objects.get_or_create(
        period_start=promo_period.CAMPAIGN_START.date(),
        period_end=promo_period.CAMPAIGN_END.date(),
        kind=DrawKind.SUPER,
        defaults={"prize_count": SUPER_DRAW_PRIZE_COUNT},
    )
    return draw


def draw_display_name(period_end: datetime.date, kind: str) -> str:
    """Человекочитаемое название конкретного розыгрыша."""
    if kind == DrawKind.SUPER:
        return f"Супер-розыгрыш {period_end.year}"
    return f"Розыгрыш за {format_date(period_end, 'F Y')}"


CODE_STATUS_LABELS = {
    "pending": "Ожидание",
    "won": "Выиграл",
    "no_win": "Без выигрыша",
}


@dataclass
class UserCodeRow:
    """Одна строка в таблице «Мои коды»."""

    code: str
    used_at: datetime.datetime
    campaign: str
    status: str
    status_display: str


@dataclass
class UserCodesSummary:
    """Список кодов пользователя с готовыми счётчиками по статусам."""

    rows: list[UserCodeRow]
    pending_count: int
    won_count: int
    no_win_count: int


def winners_months_context() -> dict[str, object]:
    """Данные для блока «Победители»: все 12 месяцев акции с вкладками.

    Там, где розыгрыш уже прошёл — реальные победители, где ещё нет — пусто.
    Используется и на главной странице, и в личном кабинете.
    """
    draws_by_month = {
        (draw.period_end.year, draw.period_end.month): draw
        for draw in (
            MonthlyDraw.objects.filter(kind=DrawKind.MONTHLY, is_finalized=True)
            .order_by("period_end")
            .prefetch_related(
                "winners__prize", "winners__user", "winners__promo_code"
            )
        )
    }
    year = promo_period.CAMPAIGN_START.year
    winners_months = [
        {
            "label": format_date(datetime.date(year, month, 1), "F"),
            "draw": draws_by_month.get((year, month)),
        }
        for month in range(1, 13)
    ]
    finalized_indexes = [
        i for i, month in enumerate(winners_months) if month["draw"]
    ]
    winners_active_index = finalized_indexes[-1] if finalized_indexes else 0
    return {
        "winners_months": winners_months,
        "winners_active_index": winners_active_index,
    }


def list_user_codes(user: User) -> UserCodesSummary:
    """Промокоды пользователя со статусом каждого — для «Моих кодов» в ЛК."""
    codes = PromoCode.objects.filter(
        used_by=user, used_at__isnull=False
    ).order_by("-used_at")
    winners_by_code = {
        winner.promo_code_id: winner
        for winner in Winner.objects.filter(
            promo_code__used_by=user
        ).select_related("draw")
    }
    monthly_draws_by_period = {
        (draw.period_start, draw.period_end): draw
        for draw in MonthlyDraw.objects.filter(kind=DrawKind.MONTHLY)
    }

    rows: list[UserCodeRow] = []
    pending_count = won_count = no_win_count = 0
    for promo_code in codes:
        assert promo_code.used_at is not None
        winner = winners_by_code.get(promo_code.pk)
        if winner is not None:
            status = "won"
            won_count += 1
            campaign = draw_display_name(
                winner.draw.period_end, winner.draw.kind
            )
        else:
            used_date = promo_code.used_at.astimezone(MOSCOW_TZ).date()
            period = promo_period.monthly_period_for_date(used_date)
            if period is None:
                campaign = draw_display_name(
                    promo_period.CAMPAIGN_END.date(), DrawKind.SUPER
                )
                status = "pending"
                pending_count += 1
            else:
                period_start, period_end = period
                draw = monthly_draws_by_period.get((period_start, period_end))
                campaign = draw_display_name(period_end, DrawKind.MONTHLY)
                if draw is not None and draw.is_finalized:
                    status = "no_win"
                    no_win_count += 1
                else:
                    status = "pending"
                    pending_count += 1
        rows.append(
            UserCodeRow(
                code=promo_code.code,
                used_at=promo_code.used_at,
                campaign=campaign,
                status=status,
                status_display=CODE_STATUS_LABELS[status],
            )
        )

    return UserCodesSummary(
        rows=rows,
        pending_count=pending_count,
        won_count=won_count,
        no_win_count=no_win_count,
    )
