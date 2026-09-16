from __future__ import annotations

import zipfile
from dataclasses import dataclass

import openpyxl
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.giveaway import promo_period
from promo_draw.celery import safe_delay

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
    FailureReason.CAMPAIGN_NOT_STARTED: (
        "Акция ещё не началась — загляните позже."
    ),
    FailureReason.CAMPAIGN_ENDED: (
        "Акция уже завершена, ввод промокодов закрыт."
    ),
    FailureReason.PERIOD_TRANSITION: (
        "Идёт подведение итогов текущего периода — приём кодов "
        "возобновится завтра."
    ),
}


@dataclass
class RedemptionResult:
    """Результат попытки погашения промокода — для показа пользователю."""

    success: bool
    message: str
    failure_reason: str | None = None
    promo_code: PromoCode | None = None


def redeem_code(user: User, code_input: str) -> RedemptionResult:
    """Погашает промокод: окно акции, бан, профиль, поиск и использование."""
    code_input = code_input.strip().upper()

    now = timezone.now()
    if now < promo_period.CAMPAIGN_START:
        return _fail(user, code_input, FailureReason.CAMPAIGN_NOT_STARTED)
    if now > promo_period.CAMPAIGN_END:
        return _fail(user, code_input, FailureReason.CAMPAIGN_ENDED)
    if promo_period.is_in_draw_transition_window(now):
        return _fail(user, code_input, FailureReason.PERIOD_TRANSITION)

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

    safe_delay(send_promo_registered_email, promo_code.pk)

    return RedemptionResult(
        success=True,
        message="Промокод принят! Вы участвуете в розыгрыше.",
        promo_code=promo_code,
    )


IMPORT_BATCH_SIZE = 2000


@dataclass
class ImportResult:
    """Итог загрузки промокодов из xlsx — для отчёта в админке."""

    total_rows: int
    added: int
    rejected_invalid_format: int
    rejected_duplicate: int


def _import_batch(batch: list[str], seen: set[str]) -> tuple[int, int]:
    """Пишет одну пачку кодов, возвращает (добавлено, дублей).

    `seen` копится по всему файлу — ловит дубль внутри ещё не
    закоммиченной пачки, который SELECT по этой же пачке не увидит.
    """
    existing = set(
        PromoCode.objects.filter(code__in=batch).values_list("code", flat=True)
    )
    new_codes = []
    rejected_duplicate = 0
    for code in batch:
        if code in existing or code in seen:
            rejected_duplicate += 1
            continue
        seen.add(code)
        new_codes.append(code)

    PromoCode.objects.bulk_create(
        [PromoCode(code=code) for code in new_codes], ignore_conflicts=True
    )
    return len(new_codes), rejected_duplicate


def import_promo_codes_from_xlsx(file: UploadedFile) -> ImportResult:
    """Читает первый столбец xlsx-файла и добавляет новые промокоды.

    Отбрасывает строки неверного формата и дубли — как внутри самого файла,
    так и уже существующие в базе. Читает и пишет пачками, а не всё разом.
    """
    try:
        workbook = openpyxl.load_workbook(file, read_only=True)
    except (zipfile.BadZipFile, KeyError) as error:
        raise ValidationError(
            "Файл не читается как xlsx — проверьте, что это не .xls и "
            "не повреждён."
        ) from error
    sheet = workbook.active

    total_rows = 0
    added = 0
    rejected_invalid_format = 0
    rejected_duplicate = 0
    seen: set[str] = set()
    batch: list[str] = []

    for row in sheet.iter_rows(values_only=True):
        if not row or row[0] is None:
            continue
        value = str(row[0]).strip().upper()
        if not value:
            continue
        total_rows += 1

        try:
            code_validator(value)
        except ValidationError:
            rejected_invalid_format += 1
            continue

        batch.append(value)
        if len(batch) >= IMPORT_BATCH_SIZE:
            batch_added, batch_rejected = _import_batch(batch, seen)
            added += batch_added
            rejected_duplicate += batch_rejected
            batch = []

    if batch:
        batch_added, batch_rejected = _import_batch(batch, seen)
        added += batch_added
        rejected_duplicate += batch_rejected

    return ImportResult(
        total_rows=total_rows,
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
