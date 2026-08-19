from __future__ import annotations

from django.db import models


class DailyStats(models.Model):
    """Статистика акции за один день — заполняется при закрытии дня."""

    date = models.DateField(unique=True)
    users_registered = models.PositiveIntegerField(default=0)
    promo_success = models.PositiveIntegerField(default=0)
    promo_failed = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "дневная статистика"
        verbose_name_plural = "дневная статистика"
        ordering = ["-date"]

    def __str__(self) -> str:
        return str(self.date)
