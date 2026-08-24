from __future__ import annotations

import datetime

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone

phone_validator = RegexValidator(
    r"^\+79\d{9}$", "Телефон должен быть в формате +79XXXXXXXXX."
)

MIN_BIRTH_DATE = datetime.date(1900, 1, 1)


def validate_birth_date(value: datetime.date) -> None:
    """Дата рождения не может быть в будущем или неправдоподобно ранней."""
    if value > timezone.localdate():
        raise ValidationError("Дата рождения не может быть в будущем.")
    if value < MIN_BIRTH_DATE:
        raise ValidationError("Проверьте дату рождения — слишком ранняя.")


def normalize_phone(raw: str) -> str:
    """Приводит российский номер телефона к виду +79XXXXXXXXX."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 11 and digits[0] in "78":
        digits = "7" + digits[1:]
    elif len(digits) == 10 and digits[0] == "9":
        digits = "7" + digits
    else:
        digits = ""
    if len(digits) != 11 or digits[1] != "9":
        raise ValidationError("Введите номер телефона в формате +79XXXXXXXXX.")
    return f"+{digits}"
