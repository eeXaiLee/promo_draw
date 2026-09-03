from __future__ import annotations

import datetime
import secrets
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from django.db import transaction
from django.template.defaultfilters import date as format_date

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


CAMPAIGN_START = datetime.date(2026, 2, 9)
CAMPAIGN_END = datetime.date(2026, 12, 31)
SUPER_DRAW_PRIZE_COUNT = 4


def get_or_create_super_draw() -> MonthlyDraw:
    """Супер-розыгрыш — разовое событие в конце акции, билеты за весь
    срок акции (09.02–31.12.2026), без исключения прошлых победителей
    ежемесячных розыгрышей."""
    draw, _ = MonthlyDraw.objects.get_or_create(
        period_start=CAMPAIGN_START,
        period_end=CAMPAIGN_END,
        kind=DrawKind.SUPER,
        defaults={"prize_count": SUPER_DRAW_PRIZE_COUNT},
    )
    return draw


def _monthly_period_for_date(
    day: datetime.date,
) -> tuple[datetime.date, datetime.date]:
    """Ежемесячный период, в который попадает дата."""
    if day.day >= 10:
        start_month, start_year = day.month, day.year
    else:
        start_month, start_year = (
            (12, day.year - 1) if day.month == 1 else (day.month - 1, day.year)
        )
    period_start = datetime.date(start_year, start_month, 10)
    end_month, end_year = (
        (1, start_year + 1)
        if start_month == 12
        else (start_month + 1, start_year)
    )
    period_end = datetime.date(end_year, end_month, 9)
    return period_start, period_end


def _draw_display_name(period_end: datetime.date, kind: str) -> str:
    """Название акции для колонки «Акция» в «Моих кодах»."""
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
        draw.period_end.month: draw
        for draw in (
            MonthlyDraw.objects.filter(kind=DrawKind.MONTHLY, is_finalized=True)
            .order_by("period_end")
            .prefetch_related(
                "winners__prize", "winners__user", "winners__promo_code"
            )
        )
    }
    winners_months = [
        {
            "label": format_date(datetime.date(2026, month, 1), "F"),
            "draw": draws_by_month.get(month),
        }
        for month in range(1, 13)
    ]
    winners_active_index = next(
        (i for i, month in enumerate(winners_months) if month["draw"]), 0
    )
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
            campaign = _draw_display_name(
                winner.draw.period_end, winner.draw.kind
            )
        else:
            used_date = promo_code.used_at.astimezone(MOSCOW_TZ).date()
            period_start, period_end = _monthly_period_for_date(used_date)
            draw = monthly_draws_by_period.get((period_start, period_end))
            campaign = _draw_display_name(period_end, DrawKind.MONTHLY)
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
