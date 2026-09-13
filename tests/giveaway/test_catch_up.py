from __future__ import annotations

import datetime

from apps.accounts.models import User
from apps.giveaway.models import MonthlyDraw, Prize, Winner
from apps.giveaway.services import moscow_day_bounds
from apps.giveaway.tasks import catch_up_monthly_draws
from apps.promocodes.models import PromoCode

PAST_PERIOD_START = datetime.date(2026, 2, 9)
PAST_PERIOD_END = datetime.date(2026, 3, 9)


def _redeem(user: User, code: str, date: datetime.date) -> PromoCode:
    day_start, _ = moscow_day_bounds(date)
    return PromoCode.objects.create(
        code=code,
        used_by=user,
        used_at=day_start + datetime.timedelta(hours=12),
    )


def test_catch_up_finalizes_a_missed_past_period(
    two_prizes: list[Prize],
) -> None:
    """Розыгрыш, чей день уже прошёл, но не был закрыт."""
    user = User.objects.create_user(email="u@example.com", password="x")
    _redeem(user, "CODE0001", PAST_PERIOD_START)

    catch_up_monthly_draws()

    draw = MonthlyDraw.objects.get(
        period_start=PAST_PERIOD_START, period_end=PAST_PERIOD_END
    )
    assert draw.is_finalized
    assert Winner.objects.filter(draw=draw).count() == 1


def test_catch_up_does_not_double_finalize(two_prizes: list[Prize]) -> None:
    """Повторный запуск подстраховки не создаёт вторую пачку победителей."""
    user = User.objects.create_user(email="u@example.com", password="x")
    _redeem(user, "CODE0001", PAST_PERIOD_START)

    catch_up_monthly_draws()
    catch_up_monthly_draws()

    draw = MonthlyDraw.objects.get(
        period_start=PAST_PERIOD_START, period_end=PAST_PERIOD_END
    )
    assert Winner.objects.filter(draw=draw).count() == 1
