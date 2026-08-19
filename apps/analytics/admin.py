from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from .models import DailyStats
from .services import build_daily_stats_workbook


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "users_registered",
        "promo_success",
        "promo_failed",
    )
    ordering = ("-date",)
    actions = ["export_to_excel"]

    @admin.action(description="Экспортировать в Excel")
    def export_to_excel(
        self, request: HttpRequest, queryset: QuerySet[DailyStats]
    ) -> HttpResponse:
        workbook = build_daily_stats_workbook(queryset.order_by("date"))
        response = HttpResponse(
            content_type=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            )
        )
        response["Content-Disposition"] = (
            'attachment; filename="daily_stats.xlsx"'
        )
        workbook.save(response)
        return response
