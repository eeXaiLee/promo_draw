from __future__ import annotations

from django.contrib import admin

from .models import PromoCode


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "used_by", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("code", "used_by__email")
    readonly_fields = ("used_by", "used_at", "created_at")
