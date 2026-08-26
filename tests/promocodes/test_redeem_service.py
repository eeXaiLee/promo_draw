from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.promocodes.models import PromoCode
from apps.promocodes.services import redeem_code


def test_redeem_code_success(complete_user: User) -> None:
    code = PromoCode.objects.create(code="AAAA1111")

    result = redeem_code(complete_user, "AAAA1111")

    assert result.success
    code.refresh_from_db()
    assert code.used_by_id == complete_user.pk
    assert code.used_at is not None


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
