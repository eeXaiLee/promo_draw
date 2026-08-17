from __future__ import annotations

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models

code_validator = RegexValidator(
    r"^[A-Z0-9]{8}$",
    "Промокод должен состоять из 8 заглавных латинских букв и цифр.",
)


class PromoCode(models.Model):
    """Промокод акции. Погашается один раз конкретным пользователем."""

    code = models.CharField(
        max_length=8, unique=True, validators=[code_validator]
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
