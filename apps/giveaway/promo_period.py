from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

DRAW_HOUR = 21
"""Розыгрыш проходит в 21:00 по Москве каждое 9-е число."""

CAMPAIGN_START = datetime.datetime(2026, 2, 9, 0, 0, tzinfo=MOSCOW_TZ)
CAMPAIGN_END = datetime.datetime(2026, 12, 31, 23, 59, 59, tzinfo=MOSCOW_TZ)

MONTHLY_DRAW_MONTHS = range(3, 13)
"""Ежемесячные розыгрыши проходят с марта по декабрь — ровно 10 штук."""


def monthly_draw_dates() -> list[datetime.date]:
    """9-е число каждого месяца с марта по декабрь года начала акции."""
    year = CAMPAIGN_START.year
    return [datetime.date(year, month, 9) for month in MONTHLY_DRAW_MONTHS]


def monthly_periods() -> list[tuple[datetime.date, datetime.date]]:
    """Все периоды ежемесячных розыгрышей: (первый день приёма кодов, день
    розыгрыша).

    Первый период начинается прямо со старта акции (9 февраля). Каждый
    следующий — со дня после розыгрыша предыдущего периода, до дня
    очередного розыгрыша включительно.
    """
    draw_dates = monthly_draw_dates()
    period_starts = [
        CAMPAIGN_START.date(),
        *(date + datetime.timedelta(days=1) for date in draw_dates[:-1]),
    ]
    return list(zip(period_starts, draw_dates))


def monthly_period_ending_on(
    day: datetime.date,
) -> tuple[datetime.date, datetime.date] | None:
    """Период, чей розыгрыш назначен на дату `day` — если такой есть."""
    for period_start, period_end in monthly_periods():
        if period_end == day:
            return period_start, period_end
    return None


def monthly_period_for_date(
    day: datetime.date,
) -> tuple[datetime.date, datetime.date] | None:
    """Период, в который попадает дата `day` — если она вообще относится к
    какому-то ежемесячному розыгрышу.

    Возвращает `None` для дат до старта акции и для «хвоста» акции после
    последнего месячного розыгрыша (10–31 декабря).
    """
    for period_start, period_end in monthly_periods():
        if period_start <= day <= period_end:
            return period_start, period_end
    return None


def is_campaign_live(moment: datetime.datetime) -> bool:
    """Идёт ли акция в момент `moment` (с учётом старта и конца)."""
    return CAMPAIGN_START <= moment <= CAMPAIGN_END


def is_in_draw_transition_window(moment: datetime.datetime) -> bool:
    """Идёт ли сейчас «окно розыгрыша» — с момента розыгрыша (21:00 9-го
    числа) до полуночи, когда приём кодов на новый период ещё не открыт.

    Действует только вокруг настоящих розыгрышей (март–декабрь) — у старта
    акции (9 февраля) такого окна нет.
    """
    moment_msk = moment.astimezone(MOSCOW_TZ)
    if moment_msk.date() not in monthly_draw_dates():
        return False
    boundary_moment = datetime.datetime.combine(
        moment_msk.date(), datetime.time(DRAW_HOUR, 0), MOSCOW_TZ
    )
    return moment_msk >= boundary_moment
