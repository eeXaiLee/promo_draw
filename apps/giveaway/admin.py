from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.analytics.services import record_daily_stats

from .models import DailyDraw, Prize, Winner
from .services import finalize_draw


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(DailyDraw)
class DailyDrawAdmin(admin.ModelAdmin):
    list_display = ("date", "is_finalized")
    list_filter = ("is_finalized",)
    actions = ["finalize_manually"]

    def get_readonly_fields(
        self, request: HttpRequest, obj: DailyDraw | None = None
    ) -> tuple[str, ...]:
        if obj is None:
            return ("is_finalized",)
        return ("date", "is_finalized")

    @admin.action(description="Определить победителя вручную")
    def finalize_manually(
        self, request: HttpRequest, queryset: QuerySet[DailyDraw]
    ) -> None:
        total_winners = 0
        for draw in queryset:
            winners = finalize_draw(draw, determined_manually=True)
            total_winners += len(winners)
            record_daily_stats(draw.date)
        self.message_user(request, f"Определено победителей: {total_winners}")


@admin.register(Winner)
class WinnerAdmin(admin.ModelAdmin):
    list_display = (
        "draw",
        "prize",
        "user",
        "determined_manually",
        "created_at",
        "email_sent_at",
    )
    list_filter = ("determined_manually",)
    search_fields = ("user__email", "prize__title")
    readonly_fields = (
        "draw",
        "prize",
        "user",
        "promo_code",
        "determined_manually",
        "created_at",
        "email_sent_at",
    )
