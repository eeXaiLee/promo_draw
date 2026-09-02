from __future__ import annotations

from django.contrib import admin
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
        for draw in queryset:
            winners = finalize_draw(draw, determined_by=request.user)
            total_winners += len(winners)
        self.message_user(request, f"Определено победителей: {total_winners}")


@admin.register(Winner)
class WinnerAdmin(admin.ModelAdmin):
    list_display = (
        "draw",
        "prize",
        "user",
        "kind",
        "determined_manually",
        "determined_by",
        "created_at",
        "email_sent_at",
    )
    list_filter = ("kind", "determined_manually")
    search_fields = ("user__email", "prize__title")
    readonly_fields = (
        "draw",
        "prize",
        "user",
        "kind",
        "promo_code",
        "determined_manually",
        "determined_by",
        "created_at",
        "email_sent_at",
    )
