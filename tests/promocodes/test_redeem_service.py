from __future__ import annotations

import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.accounts.models import User
from apps.promocodes.models import PromoCode
from apps.promocodes.services import redeem_code

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def test_redeem_code_success(complete_user: User) -> None:
    code = PromoCode.objects.create(code="AAAA1111")

    result = redeem_code(complete_user, "AAAA1111")

    assert result.success
    code.refresh_from_db()
    assert code.used_by_id == complete_user.pk
    assert code.used_at is not None


def test_redeem_code_succeeds_even_if_email_task_fails(
    complete_user: User,
) -> None:
    """Падение брокера при постановке письма не должно рвать погашение."""
    code = PromoCode.objects.create(code="ZZZZ9999")

    with patch(
        "apps.promocodes.services.send_promo_registered_email.delay",
        side_effect=OSError("broker unavailable"),
    ):
        result = redeem_code(complete_user, "ZZZZ9999")

    assert result.success
    code.refresh_from_db()
    assert code.used_by_id == complete_user.pk


def test_redeem_code_already_used(complete_user: User) -> None:
    other = User.objects.create_user(
        email="other@example.com", password="testpass123"
    )
    PromoCode.objects.create(
        code="BBBB2222", used_by=other, used_at=timezone.now()
    )

    result = redeem_code(complete_user, "BBBB2222")

    assert not result.success
    assert result.failure_reason == "already_used"
    assert result.message == "Этот промокод уже был использован."


def test_redeem_code_email_not_confirmed(complete_user: User) -> None:
    """Без подтверждённой почты промокод не принимается."""
    complete_user.email_confirmed = False
    complete_user.save(update_fields=["email_confirmed"])
    PromoCode.objects.create(code="CCCC3333")

    result = redeem_code(complete_user, "CCCC3333")

    assert not result.success
    assert result.failure_reason == "email_not_confirmed"


def test_redeem_code_before_campaign_start(complete_user: User) -> None:
    """До старта акции код не принимается, даже если он существует."""
    PromoCode.objects.create(code="DDDD4444")
    before_start = datetime.datetime(2026, 1, 1, tzinfo=MOSCOW_TZ)

    with patch(
        "apps.promocodes.services.timezone.now", return_value=before_start
    ):
        result = redeem_code(complete_user, "DDDD4444")

    assert not result.success
    assert result.failure_reason == "campaign_not_started"


def test_redeem_code_after_campaign_end(complete_user: User) -> None:
    """После конца акции код больше не гасится."""
    PromoCode.objects.create(code="EEEE5555")
    after_end = datetime.datetime(2027, 1, 2, tzinfo=MOSCOW_TZ)

    with patch("apps.promocodes.services.timezone.now", return_value=after_end):
        result = redeem_code(complete_user, "EEEE5555")

    assert not result.success
    assert result.failure_reason == "campaign_ended"


def test_redeem_code_during_draw_transition_window(complete_user: User) -> None:
    """С момента розыгрыша (21:00 9-го числа) до полуночи код не гасится."""
    PromoCode.objects.create(code="FFFF6666")
    during_transition = datetime.datetime(2026, 3, 9, 22, 0, tzinfo=MOSCOW_TZ)

    with patch(
        "apps.promocodes.services.timezone.now",
        return_value=during_transition,
    ):
        result = redeem_code(complete_user, "FFFF6666")

    assert not result.success
    assert result.failure_reason == "period_transition"


def test_redeem_code_right_after_transition_window(complete_user: User) -> None:
    """С полуночи приём кодов на новый период уже открыт."""
    PromoCode.objects.create(code="GGGG7777")
    just_after_midnight = datetime.datetime(
        2026, 3, 10, 0, 30, tzinfo=MOSCOW_TZ
    )

    with patch(
        "apps.promocodes.services.timezone.now",
        return_value=just_after_midnight,
    ):
        result = redeem_code(complete_user, "GGGG7777")

    assert result.success


def test_redeem_code_bans_after_three_failed_attempts(
    complete_user: User,
) -> None:
    for _ in range(3):
        result = redeem_code(complete_user, "NOPE0000")
        assert not result.success
        assert result.failure_reason == "not_found"

    result = redeem_code(complete_user, "NOPE0000")

    assert not result.success
    assert result.failure_reason == "banned"
