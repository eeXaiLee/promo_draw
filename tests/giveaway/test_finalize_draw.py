from __future__ import annotations

import datetime

from apps.accounts.models import User
from apps.giveaway.models import DailyDraw, Prize, Winner
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


def test_finalize_draw_picks_winners_from_redeemed_codes(
    two_prizes: list[Prize],
) -> None:
    """3 участника и 2 приза → победителей ровно 2, и это разные люди."""
    draw = DailyDraw.objects.create(date=DRAW_DATE)
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


def test_finalize_draw_manual_and_automatic_dont_double_finalize(
    two_prizes: list[Prize],
) -> None:
    """Ручной запуск и авто-таска для одного дня не должны создать дубли."""
    draw = DailyDraw.objects.create(date=DRAW_DATE)
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


def test_finalize_draw_excludes_users_who_already_won(
    two_prizes: list[Prize],
) -> None:
    """Победивший ранее не попадает в победители снова, даже с новым кодом."""
    already_won_user = User.objects.create_user(
        email="past_winner@example.com", password="x"
    )
    other_users = [
        User.objects.create_user(email=f"u{i}@example.com", password="x")
        for i in range(2)
    ]

    past_date = DRAW_DATE - datetime.timedelta(days=1)
    past_draw = DailyDraw.objects.create(date=past_date, is_finalized=True)
    past_code = _redeem(already_won_user, "PASTCODE", past_date)
    Winner.objects.create(
        draw=past_draw,
        prize=two_prizes[0],
        user=already_won_user,
        promo_code=past_code,
    )

    draw = DailyDraw.objects.create(date=DRAW_DATE)
    _redeem(already_won_user, "TODAY001", DRAW_DATE)
    for i, user in enumerate(other_users):
        _redeem(user, f"TODAY10{i}", DRAW_DATE)

    winners = finalize_draw(draw)

    winner_user_ids = {w.user_id for w in winners}
    assert already_won_user.pk not in winner_user_ids
    assert winner_user_ids == {u.pk for u in other_users}
