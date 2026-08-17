from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import PromoCode, PromoRedemptionAttempt
from .rate_limit import get_ban_message, register_failed_attempt

FailureReason = PromoRedemptionAttempt.FailureReason

FAILURE_MESSAGES: dict[str, str] = {
    FailureReason.PROFILE_INCOMPLETE: (
        "Сначала заполните профиль — без этого промокод не принимается."
    ),
    FailureReason.NOT_FOUND: (
        "Такой промокод не найден. Проверьте, что ввели его без ошибок."
    ),
    FailureReason.ALREADY_USED: "Этот промокод уже был использован.",
}


@dataclass
class RedemptionResult:
    """Результат попытки погашения промокода — для показа пользователю."""

    success: bool
    message: str
    failure_reason: str | None = None
    promo_code: PromoCode | None = None


def redeem_code(user: User, code_input: str) -> RedemptionResult:
    """Погашает промокод: бан, профиль, поиск кода и использование."""
    code_input = code_input.strip().upper()

    ban_message = get_ban_message(user.pk)
    if ban_message is not None:
        return _fail(
            user, code_input, FailureReason.BANNED, message=ban_message
        )

    if not user.profile_is_complete:
        return _fail(user, code_input, FailureReason.PROFILE_INCOMPLETE)

    with transaction.atomic():
        promo_code = (
            PromoCode.objects.select_for_update()
            .filter(code=code_input)
            .first()
        )
        if promo_code is None:
            register_failed_attempt(user.pk)
            return _fail(user, code_input, FailureReason.NOT_FOUND)

        if promo_code.used_by_id is not None:
            register_failed_attempt(user.pk)
            return _fail(
                user, code_input, FailureReason.ALREADY_USED, promo_code
            )

        promo_code.used_by = user
        promo_code.used_at = timezone.now()
        promo_code.save(update_fields=["used_by", "used_at"])
        PromoRedemptionAttempt.objects.create(
            user=user, code_input=code_input, success=True
        )

    return RedemptionResult(
        success=True,
        message="Промокод принят! Вы участвуете в розыгрыше.",
        promo_code=promo_code,
    )


def _fail(
    user: User,
    code_input: str,
    reason: FailureReason,
    promo_code: PromoCode | None = None,
    message: str | None = None,
) -> RedemptionResult:
    PromoRedemptionAttempt.objects.create(
        user=user,
        code_input=code_input,
        success=False,
        failure_reason=reason,
    )
    return RedemptionResult(
        success=False,
        message=message or FAILURE_MESSAGES[reason],
        failure_reason=reason,
        promo_code=promo_code,
    )
