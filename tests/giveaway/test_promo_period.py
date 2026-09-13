from __future__ import annotations

import datetime

from apps.giveaway import promo_period


def test_monthly_periods_are_exactly_ten_march_to_december() -> None:
    """Акция «10 месяцев побед» — ровно 10 розыгрышей, март—декабрь."""
    periods = promo_period.monthly_periods()

    assert len(periods) == 10
    assert periods[0] == (
        datetime.date(2026, 2, 9),
        datetime.date(2026, 3, 9),
    )
    assert periods[-1] == (
        datetime.date(2026, 11, 10),
        datetime.date(2026, 12, 9),
    )


def test_monthly_period_for_date_none_after_last_draw() -> None:
    """10–31 декабря — хвост акции без месячного периода (только супер)."""
    assert (
        promo_period.monthly_period_for_date(datetime.date(2026, 12, 20))
        is None
    )
    assert promo_period.monthly_period_for_date(datetime.date(2026, 12, 9)) == (
        datetime.date(2026, 11, 10),
        datetime.date(2026, 12, 9),
    )


def test_monthly_period_for_date_none_before_campaign_start() -> None:
    """До 9 февраля (старт акции) периода ещё нет — с 9-го он уже есть."""
    assert (
        promo_period.monthly_period_for_date(datetime.date(2026, 2, 8)) is None
    )
    assert promo_period.monthly_period_for_date(datetime.date(2026, 2, 9)) == (
        datetime.date(2026, 2, 9),
        datetime.date(2026, 3, 9),
    )
