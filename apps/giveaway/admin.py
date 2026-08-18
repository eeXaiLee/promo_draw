from __future__ import annotations

from django.contrib import admin

from .models import DailyDraw, Prize, Winner


@admin.register(Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title",)


@admin.register(DailyDraw)
class DailyDrawAdmin(admin.ModelAdmin):
    list_display = ("date", "is_finalized")
    list_filter = ("is_finalized",)
    readonly_fields = ("date", "is_finalized")


@admin.register(Winner)
class WinnerAdmin(admin.ModelAdmin):
    list_display = (
        "draw",
        "prize",
        "user",
        "determined_manually",
        "created_at",
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
    )
