from __future__ import annotations

from dataclasses import dataclass

import openpyxl
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import PromoCode, PromoRedemptionAttempt, code_validator
from .rate_limit import get_ban_message, register_failed_attempt
from .tasks import send_promo_registered_email

FailureReason = PromoRedemptionAttempt.FailureReason

FAILURE_MESSAGES: dict[str, str] = {
    FailureReason.EMAIL_NOT_CONFIRMED: (
        "Сначала подтвердите почту по ссылке из письма — без этого "
        "промокод не принимается."
    ),
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

    if not user.email_confirmed:
        return _fail(user, code_input, FailureReason.EMAIL_NOT_CONFIRMED)

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

    send_promo_registered_email.delay(promo_code.pk)

    return RedemptionResult(
        success=True,
        message="Промокод принят! Вы участвуете в розыгрыше.",
        promo_code=promo_code,
    )


@dataclass
class ImportResult:
    """Итог загрузки промокодов из xlsx — для отчёта в админке."""

    total_rows: int
    added: int
    rejected_invalid_format: int
    rejected_duplicate: int


def import_promo_codes_from_xlsx(file: UploadedFile) -> ImportResult:
    """Читает первый столбец xlsx-файла и добавляет новые промокоды.

    Отбрасывает строки неверного формата и дубли — как внутри самого
    файла, так и уже существующие в базе.
    """
    workbook = openpyxl.load_workbook(file, read_only=True)
    sheet = workbook.active

    raw_values = []
    for row in sheet.iter_rows(values_only=True):
        if not row or row[0] is None:
            continue
        value = str(row[0]).strip().upper()
        if value:
            raw_values.append(value)

    valid_codes = []
    rejected_invalid_format = 0
    for value in raw_values:
        try:
            code_validator(value)
        except ValidationError:
            rejected_invalid_format += 1
        else:
            valid_codes.append(value)

    existing = set(
        PromoCode.objects.filter(code__in=valid_codes).values_list(
            "code", flat=True
        )
    )

    seen: set[str] = set()
    new_codes = []
    rejected_duplicate = 0
    for code in valid_codes:
        if code in existing or code in seen:
            rejected_duplicate += 1
            continue
        seen.add(code)
        new_codes.append(code)

    PromoCode.objects.bulk_create(
        [PromoCode(code=code) for code in new_codes],
        batch_size=1000,
        ignore_conflicts=True,
    )
    added = len(new_codes)

    return ImportResult(
        total_rows=len(raw_values),
        added=added,
        rejected_invalid_format=rejected_invalid_format,
        rejected_duplicate=rejected_duplicate,
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
