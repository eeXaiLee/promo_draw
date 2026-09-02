from __future__ import annotations

from django.conf import settings
from django.db import models


class DrawKind(models.TextChoices):
    """Вид розыгрыша — влияет на пул призов и число победителей."""

    MONTHLY = "monthly", "Ежемесячный"
    SUPER = "super", "Супер-розыгрыш"


class MonthlyDraw(models.Model):
    """Розыгрыш за период. Финализируется ровно один раз."""

    period_start = models.DateField()
    period_end = models.DateField()
    kind = models.CharField(
        max_length=10, choices=DrawKind.choices, default=DrawKind.MONTHLY
    )
    prize_count = models.PositiveSmallIntegerField(default=2)
    is_finalized = models.BooleanField(default=False)

    class Meta:
        verbose_name = "розыгрыш"
        verbose_name_plural = "розыгрыши"
        ordering = ["-period_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["period_start", "period_end", "kind"],
                name="one_draw_per_period_kind",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.period_start}–{self.period_end} ({self.get_kind_display()})"
        )


class Prize(models.Model):
    """Приз в пуле акции — не привязан к конкретному розыгрышу."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    kind = models.CharField(
        max_length=10, choices=DrawKind.choices, default=DrawKind.MONTHLY
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "приз"
        verbose_name_plural = "призы"

    def __str__(self) -> str:
        return self.title


class Winner(models.Model):
    """Победитель конкретного розыгрыша — один приз, один пользователь.

    Один человек может выиграть не больше одного раза на вид розыгрыша
    (`kind`) — победа в ежемесячном не исключает участие в супер-розыгрыше.
    """

    draw = models.ForeignKey(
        MonthlyDraw, on_delete=models.CASCADE, related_name="winners"
    )
    prize = models.ForeignKey(
        Prize, on_delete=models.PROTECT, related_name="winners"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="giveaway_wins",
    )
    kind = models.CharField(max_length=10, choices=DrawKind.choices)
    promo_code = models.ForeignKey(
        "promocodes.PromoCode",
        on_delete=models.PROTECT,
        related_name="giveaway_wins",
    )
    determined_manually = models.BooleanField(default=False)
    determined_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manual_draws",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "победитель"
        verbose_name_plural = "победители"
        constraints = [
            models.UniqueConstraint(
                fields=["draw", "prize"], name="one_winner_per_draw_prize"
            ),
            models.UniqueConstraint(
                fields=["user", "kind"], name="one_win_per_kind"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} — {self.prize} ({self.draw})"
