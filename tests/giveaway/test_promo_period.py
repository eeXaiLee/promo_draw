from __future__ import annotations

import datetime

from apps.giveaway import promo_period

MSK = promo_period.MOSCOW_TZ


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


def test_next_draw_moment_before_first_draw() -> None:
    """До 9 марта 21:00 ближайший розыгрыш — он самый первый."""
    moment = datetime.datetime(2026, 3, 1, tzinfo=MSK)

    assert promo_period.next_draw_moment(moment) == datetime.datetime(
        2026, 3, 9, 21, 0, tzinfo=MSK
    )


def test_next_draw_moment_right_after_a_draw_is_the_next_one() -> None:
    """Сразу после розыгрыша таймер должен целиться в следующий месяц,
    а не показывать 0 бесконечно."""
    moment = datetime.datetime(2026, 3, 9, 21, 0, 1, tzinfo=MSK)

    assert promo_period.next_draw_moment(moment) == datetime.datetime(
        2026, 4, 9, 21, 0, tzinfo=MSK
    )


def test_next_draw_moment_after_last_monthly_draw_is_super_draw() -> None:
    """После последнего месячного (9 декабря) остаётся только супер."""
    moment = datetime.datetime(2026, 12, 20, tzinfo=MSK)

    assert (
        promo_period.next_draw_moment(moment) == promo_period.SUPER_DRAW_MOMENT
    )


def test_next_draw_moment_none_after_super_draw() -> None:
    """После супер-розыгрыша больше нечего ждать — таймер должен исчезнуть."""
    moment = promo_period.SUPER_DRAW_MOMENT + datetime.timedelta(seconds=1)

    assert promo_period.next_draw_moment(moment) is None
