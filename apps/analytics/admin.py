from __future__ import annotations

from django.contrib import admin

from .models import DailyStats


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "users_registered",
        "promo_success",
        "promo_failed",
    )
    ordering = ("-date",)
