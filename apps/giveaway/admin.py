from __future__ import annotations

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.accounts.models import User

from .models import MonthlyDraw, Prize, Winner
from .services import finalize_draw


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("title",)


@admin.register(MonthlyDraw)
class MonthlyDrawAdmin(admin.ModelAdmin):
    list_display = (
        "period_start",
        "period_end",
        "kind",
        "prize_count",
        "is_finalized",
    )
    list_filter = ("kind", "is_finalized")
    actions = ["finalize_manually"]

    def get_readonly_fields(
        self, request: HttpRequest, obj: MonthlyDraw | None = None
    ) -> tuple[str, ...]:
        if obj is None:
            return ("is_finalized",)
        return ("period_start", "period_end", "kind", "is_finalized")

    @admin.action(
        description="Определить победителя вручную", permissions=["change"]
    )
    def finalize_manually(
        self, request: HttpRequest, queryset: QuerySet[MonthlyDraw]
    ) -> None:
        assert isinstance(request.user, User)
        total_winners = 0
        short_draws = []
        for draw in queryset:
            winners = finalize_draw(draw, determined_by=request.user)
            total_winners += len(winners)
            if len(winners) < draw.prize_count:
                short_draws.append(draw)
        self.message_user(request, f"Определено победителей: {total_winners}")
        if short_draws:
            draws_text = ", ".join(str(draw) for draw in short_draws)
            self.message_user(
                request,
                f"Победителей меньше, чем призов, в розыгрышах: "
                f"{draws_text}. Проверьте пул активных призов.",
                level=messages.WARNING,
            )


@admin.register(Winner)
class WinnerAdmin(admin.ModelAdmin):
    """Победители — доступны только для чтения, в т.ч. после удаления
    аккаунта: ФИО/email/телефон сняты снимком на момент выигрыша, поэтому
    не пропадают вместе с User."""

    list_display = (
        "draw",
        "prize",
        "winner_full_name",
        "user",
        "kind",
        "determined_manually",
        "determined_by",
        "created_at",
        "email_sent_at",
    )
    list_filter = ("kind", "determined_manually")
    search_fields = ("winner_full_name", "winner_email", "prize__title")
    readonly_fields = (
        "draw",
        "prize",
        "user",
        "winner_full_name",
        "winner_email",
        "winner_phone",
        "kind",
        "promo_code",
        "determined_manually",
        "determined_by",
        "created_at",
        "email_sent_at",
    )
