from __future__ import annotations

from django.contrib import admin

from .models import PromoCode, PromoRedemptionAttempt


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "used_by", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("code", "used_by__email")
    readonly_fields = ("used_by", "used_at", "created_at")


@admin.register(PromoRedemptionAttempt)
class PromoRedemptionAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "code_input",
        "user",
        "success",
        "failure_reason",
        "created_at",
    )
    list_filter = ("success", "failure_reason")
    search_fields = ("code_input", "user__email")
    readonly_fields = (
        "user",
        "code_input",
        "success",
        "failure_reason",
        "created_at",
    )
