from __future__ import annotations

import datetime

from apps.accounts.models import User
from apps.giveaway.models import DrawKind, MonthlyDraw, Prize, Winner
from apps.giveaway.services import list_user_codes, moscow_day_bounds
from apps.promocodes.models import PromoCode

PERIOD_START = datetime.date(2030, 1, 10)
PERIOD_END = datetime.date(2030, 2, 9)
REDEEMED_ON = datetime.date(2030, 1, 20)


def _redeem(user: User, code: str, date: datetime.date) -> PromoCode:
    day_start, _ = moscow_day_bounds(date)
    return PromoCode.objects.create(
        code=code,
        used_by=user,
        used_at=day_start + datetime.timedelta(hours=12),
    )


def test_list_user_codes_pending_before_draw_finalized(db) -> None:
    """Розыгрыш периода ещё не проведён — статус «Ожидание»."""
    user = User.objects.create_user(email="u@example.com", password="x")
    _redeem(user, "CODE0001", REDEEMED_ON)

    summary = list_user_codes(user)

    assert len(summary.rows) == 1
    assert summary.rows[0].status == "pending"
    assert summary.rows[0].status_display == "Ожидание"
    assert (summary.pending_count, summary.won_count, summary.no_win_count) == (
        1,
        0,
        0,
    )


def test_list_user_codes_no_win_when_draw_finalized(db) -> None:
    """Розыгрыш периода уже финализирован, но кода нет среди победителей."""
    user = User.objects.create_user(email="u@example.com", password="x")
    _redeem(user, "CODE0001", REDEEMED_ON)
    MonthlyDraw.objects.create(
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        kind=DrawKind.MONTHLY,
        is_finalized=True,
    )

    summary = list_user_codes(user)

    assert summary.rows[0].status == "no_win"
    assert summary.no_win_count == 1


def test_list_user_codes_won(db) -> None:
    """Код, на который есть `Winner`, — «Выиграл»."""
    user = User.objects.create_user(email="u@example.com", password="x")
    code = _redeem(user, "CODE0001", REDEEMED_ON)
    draw = MonthlyDraw.objects.create(
        period_start=PERIOD_START, period_end=PERIOD_END, kind=DrawKind.MONTHLY
    )
    Winner.objects.create(
        draw=draw,
        prize=Prize.objects.create(title="Приз"),
        user=user,
        kind=DrawKind.MONTHLY,
        promo_code=code,
    )

    summary = list_user_codes(user)

    assert summary.rows[0].status == "won"
    assert summary.won_count == 1


def test_list_user_codes_counts_across_multiple_codes(db) -> None:
    """Счётчики агрегируются сразу по всем кодам пользователя."""
    user = User.objects.create_user(email="u@example.com", password="x")
    _redeem(user, "PENDING1", REDEEMED_ON)

    _redeem(user, "NOWIN001", datetime.date(2030, 3, 15))
    MonthlyDraw.objects.create(
        period_start=datetime.date(2030, 3, 10),
        period_end=datetime.date(2030, 4, 9),
        kind=DrawKind.MONTHLY,
        is_finalized=True,
    )

    won_code = _redeem(user, "WONCODE1", datetime.date(2030, 5, 15))
    won_draw = MonthlyDraw.objects.create(
        period_start=datetime.date(2030, 5, 10),
        period_end=datetime.date(2030, 6, 9),
        kind=DrawKind.MONTHLY,
    )
    Winner.objects.create(
        draw=won_draw,
        prize=Prize.objects.create(title="Приз"),
        user=user,
        kind=DrawKind.MONTHLY,
        promo_code=won_code,
    )

    summary = list_user_codes(user)

    assert len(summary.rows) == 3
    assert summary.pending_count == 1
    assert summary.no_win_count == 1
    assert summary.won_count == 1
