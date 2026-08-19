from __future__ import annotations

from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import URLPattern, path

from .forms import PromoCodeUploadForm
from .models import PromoCode, PromoRedemptionAttempt
from .services import import_promo_codes_from_xlsx


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "used_by", "used_at", "created_at")
    list_filter = ("used_at",)
    search_fields = ("code", "used_by__email")
    readonly_fields = ("used_by", "used_at", "created_at")
    change_list_template = "admin/promocodes/promocode/change_list.html"

    def get_urls(self) -> list[URLPattern]:
        custom_urls = [
            path(
                "upload/",
                self.admin_site.admin_view(self.upload_view),
                name="promocodes_promocode_upload",
            ),
        ]
        return custom_urls + super().get_urls()

    def upload_view(self, request: HttpRequest) -> HttpResponse:
        if request.method == "POST":
            form = PromoCodeUploadForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_promo_codes_from_xlsx(form.cleaned_data["file"])
                messages.success(
                    request,
                    f"Обработано строк: {result.total_rows}. "
                    f"Добавлено новых кодов: {result.added}.",
                )
                return redirect("admin:promocodes_promocode_changelist")
        else:
            form = PromoCodeUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
            "title": "Загрузка промокодов из xlsx",
        }
        return render(
            request, "admin/promocodes/promocode/upload.html", context
        )


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
