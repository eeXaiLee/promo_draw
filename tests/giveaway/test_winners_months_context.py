from __future__ import annotations

import datetime

from apps.giveaway import promo_period
from apps.giveaway.models import MonthlyDraw
from apps.giveaway.services import winners_months_context


def test_winners_active_index_points_at_latest_finalized_month(
    db: None,
) -> None:
    """Открытая по умолчанию вкладка — последний прошедший розыгрыш,
    а не первый — иначе пользователь видит устаревших победителей."""
    year = promo_period.CAMPAIGN_START.year
    MonthlyDraw.objects.create(
        period_start=datetime.date(year, 4, 9),
        period_end=datetime.date(year, 4, 9),
        is_finalized=True,
    )
    MonthlyDraw.objects.create(
        period_start=datetime.date(year, 6, 9),
        period_end=datetime.date(year, 6, 9),
        is_finalized=True,
    )

    context = winners_months_context()

    assert context["winners_active_index"] == 5
