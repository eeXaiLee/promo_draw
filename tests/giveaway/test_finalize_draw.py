from __future__ import annotations

import datetime

from apps.accounts.models import User
from apps.giveaway.models import DrawKind, MonthlyDraw, Prize, Winner
from apps.giveaway.services import finalize_draw, moscow_day_bounds
from apps.promocodes.models import PromoCode

DRAW_DATE = datetime.date(2030, 1, 15)


def _redeem(user: User, code: str, date: datetime.date) -> PromoCode:
    """Помечает код погашенным этим пользователем в середине суток `date`."""
    day_start, _ = moscow_day_bounds(date)
    return PromoCode.objects.create(
        code=code,
        used_by=user,
        used_at=day_start + datetime.timedelta(hours=12),
    )


def _monthly_draw(date: datetime.date, **kwargs: object) -> MonthlyDraw:
    return MonthlyDraw.objects.create(
        period_start=date, period_end=date, **kwargs
    )


def test_finalize_draw_picks_winners_from_redeemed_codes(
    two_prizes: list[Prize],
) -> None:
    """3 участника и 2 приза → победителей ровно 2, и это разные люди."""
    draw = _monthly_draw(DRAW_DATE)
    users = [
        User.objects.create_user(email=f"u{i}@example.com", password="x")
        for i in range(3)
    ]
    for i, user in enumerate(users):
        _redeem(user, f"CODE000{i}", DRAW_DATE)

    winners = finalize_draw(draw)

    draw.refresh_from_db()
    assert draw.is_finalized
    assert len(winners) == 2
    winner_user_ids = {w.user_id for w in winners}
    assert winner_user_ids.issubset({u.pk for u in users})
    assert len(winner_user_ids) == 2


def test_finalize_draw_counts_codes_across_whole_period(
    two_prizes: list[Prize],
) -> None:
    """Билетами становятся коды за весь период, а не только за один день —
    и коды до/после периода в розыгрыш не попадают."""
    period_start = datetime.date(2030, 3, 10)
    period_end = datetime.date(2030, 4, 9)
    draw = MonthlyDraw.objects.create(
        period_start=period_start, period_end=period_end
    )

    in_period_users = [
        User.objects.create_user(email=f"in{i}@example.com", password="x")
        for i in range(2)
    ]
    _redeem(in_period_users[0], "STARTDAY", period_start)
    _redeem(in_period_users[1], "ENDDAY01", period_end)

    before_user = User.objects.create_user(
        email="before@example.com", password="x"
    )
    _redeem(before_user, "TOOEARLY", period_start - datetime.timedelta(days=1))
    after_user = User.objects.create_user(
        email="after@example.com", password="x"
    )
    _redeem(after_user, "TOOLATE1", period_end + datetime.timedelta(days=1))

    winners = finalize_draw(draw)

    winner_user_ids = {w.user_id for w in winners}
    assert winner_user_ids == {u.pk for u in in_period_users}


def test_finalize_draw_manual_and_automatic_dont_double_finalize(
    two_prizes: list[Prize],
) -> None:
    """Ручной запуск и авто-таска для одного периода не создают дубли."""
    draw = _monthly_draw(DRAW_DATE)
    users = [
        User.objects.create_user(email=f"u{i}@example.com", password="x")
        for i in range(3)
    ]
    for i, user in enumerate(users):
        _redeem(user, f"CODE000{i}", DRAW_DATE)

    staff_user = User.objects.create_user(
        email="staff@example.com", password="x"
    )
    manual_winners = finalize_draw(draw, determined_by=staff_user)
    assert len(manual_winners) == 2
    assert all(w.determined_by_id == staff_user.pk for w in manual_winners)

    auto_winners = finalize_draw(draw)
    assert auto_winners == []
    assert Winner.objects.filter(draw=draw).count() == 2


def test_finalize_draw_excludes_users_who_already_won_same_kind(
    two_prizes: list[Prize],
) -> None:
    """Победивший ранее в том же виде розыгрыша не попадает снова."""
    already_won_user = User.objects.create_user(
        email="past_winner@example.com", password="x"
    )
    other_users = [
        User.objects.create_user(email=f"u{i}@example.com", password="x")
        for i in range(2)
    ]

    past_date = DRAW_DATE - datetime.timedelta(days=1)
    past_draw = _monthly_draw(past_date, is_finalized=True)
    past_code = _redeem(already_won_user, "PASTCODE", past_date)
    Winner.objects.create(
        draw=past_draw,
        prize=two_prizes[0],
        user=already_won_user,
        kind=DrawKind.MONTHLY,
        promo_code=past_code,
    )

    draw = _monthly_draw(DRAW_DATE)
    _redeem(already_won_user, "TODAY001", DRAW_DATE)
    for i, user in enumerate(other_users):
        _redeem(user, f"TODAY10{i}", DRAW_DATE)

    winners = finalize_draw(draw)

    winner_user_ids = {w.user_id for w in winners}
    assert already_won_user.pk not in winner_user_ids
    assert winner_user_ids == {u.pk for u in other_users}


def test_finalize_draw_super_includes_previous_monthly_winners(
    two_prizes: list[Prize],
) -> None:
    """Победа в ежемесячном не исключает участие в супер-розыгрыше."""
    for prize in two_prizes:
        prize.kind = DrawKind.SUPER
        prize.save(update_fields=["kind"])

    monthly_winner = User.objects.create_user(
        email="monthly_winner@example.com", password="x"
    )
    past_date = DRAW_DATE - datetime.timedelta(days=1)
    past_draw = _monthly_draw(past_date, is_finalized=True)
    past_code = _redeem(monthly_winner, "PASTCODE", past_date)
    Winner.objects.create(
        draw=past_draw,
        prize=Prize.objects.create(title="Приз", kind=DrawKind.MONTHLY),
        user=monthly_winner,
        kind=DrawKind.MONTHLY,
        promo_code=past_code,
    )

    super_draw = MonthlyDraw.objects.create(
        period_start=past_date,
        period_end=DRAW_DATE,
        kind=DrawKind.SUPER,
        prize_count=4,
    )
    _redeem(monthly_winner, "SUPRCODE", DRAW_DATE)

    winners = finalize_draw(super_draw)

    assert {w.user_id for w in winners} == {monthly_winner.pk}
