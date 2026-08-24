from __future__ import annotations

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

PROMO_CODE_LENGTH = 8

code_validator = RegexValidator(
    rf"^[A-Z0-9]{{{PROMO_CODE_LENGTH}}}$",
    "Промокод должен состоять из 8 заглавных латинских букв и цифр.",
)


class PromoCode(models.Model):
    """Промокод акции. Погашается один раз конкретным пользователем."""

    code = models.CharField(
        max_length=PROMO_CODE_LENGTH, unique=True, validators=[code_validator]
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="used_promo_codes",
    )
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "промокод"
        verbose_name_plural = "промокоды"

    def __str__(self) -> str:
        return self.code


class PromoRedemptionAttempt(models.Model):
    """Лог каждой попытки ввода промокода — для аналитики и аудита."""

    class FailureReason(models.TextChoices):
        NOT_FOUND = "not_found", "Код не найден"
        ALREADY_USED = "already_used", "Код уже использован"
        BANNED = "banned", "Временная блокировка"
        PROFILE_INCOMPLETE = "profile_incomplete", "Не заполнен профиль"
        EMAIL_NOT_CONFIRMED = "email_not_confirmed", "Почта не подтверждена"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="promo_attempts",
    )
    code_input = models.CharField(max_length=8)
    success = models.BooleanField(default=False)
    failure_reason = models.CharField(
        max_length=20, choices=FailureReason.choices, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "попытка ввода промокода"
        verbose_name_plural = "попытки ввода промокода"

    def __str__(self) -> str:
        status = "успех" if self.success else self.failure_reason
        return f"{self.user_id} — {self.code_input} ({status})"
