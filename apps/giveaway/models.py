from __future__ import annotations

from django.conf import settings
from django.db import models

DRAW_PRIZE_COUNT = 2


class DailyDraw(models.Model):
    """Розыгрыш за один день. Финализируется ровно один раз."""

    date = models.DateField(unique=True)
    is_finalized = models.BooleanField(default=False)

    class Meta:
        verbose_name = "розыгрыш"
        verbose_name_plural = "розыгрыши"
        ordering = ["-date"]

    def __str__(self) -> str:
        return str(self.date)


class Prize(models.Model):
    """Приз в общем пуле акции — не привязан к конкретному дню."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "приз"
        verbose_name_plural = "призы"

    def __str__(self) -> str:
        return self.title


class Winner(models.Model):
    """Победитель конкретного розыгрыша — один приз, один пользователь."""

    draw = models.ForeignKey(
        DailyDraw, on_delete=models.CASCADE, related_name="winners"
    )
    prize = models.ForeignKey(
        Prize, on_delete=models.PROTECT, related_name="winners"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="giveaway_win",
    )
    promo_code = models.ForeignKey(
        "promocodes.PromoCode",
        on_delete=models.PROTECT,
        related_name="giveaway_wins",
    )
    determined_manually = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "победитель"
        verbose_name_plural = "победители"
        constraints = [
            models.UniqueConstraint(
                fields=["draw", "prize"], name="one_winner_per_draw_prize"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.prize} ({self.draw})"
