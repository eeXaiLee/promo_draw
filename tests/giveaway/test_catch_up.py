from __future__ import annotations

import datetime
from unittest.mock import patch

from apps.accounts.models import User
from apps.giveaway import promo_period
from apps.giveaway.models import MonthlyDraw, Prize, Winner
from apps.giveaway.services import moscow_day_bounds
from apps.giveaway.tasks import catch_up_monthly_draws
from apps.promocodes.models import PromoCode

MSK = promo_period.MOSCOW_TZ

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


def test_catch_up_does_not_finalize_before_draw_hour(
    two_prizes: list[Prize],
) -> None:
    """В день розыгрыша до 21:00 подстраховка розыгрыш не трогает — иначе
    участники теряют почти сутки приёма кодов до штатного времени."""
    user = User.objects.create_user(email="u@example.com", password="x")
    _redeem(user, "CODE0002", PAST_PERIOD_START)
    just_after_midnight = datetime.datetime(2026, 3, 9, 0, 30, tzinfo=MSK)

    with patch(
        "apps.giveaway.tasks.timezone.now",
        return_value=just_after_midnight,
    ):
        catch_up_monthly_draws()

    assert not MonthlyDraw.objects.filter(
        period_start=PAST_PERIOD_START,
        period_end=PAST_PERIOD_END,
        is_finalized=True,
    ).exists()
