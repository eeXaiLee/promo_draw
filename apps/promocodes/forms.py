from __future__ import annotations

from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import PROMO_CODE_LENGTH

XLSX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

MAX_UPLOAD_SIZE_MB = 10


class PromoCodeForm(forms.Form):
    """Ввод промокода на странице погашения."""

    code = forms.CharField(
        label="Промокод",
        max_length=PROMO_CODE_LENGTH,
        widget=forms.TextInput(
            attrs={
                "placeholder": "XXXXXXXXXXXXXXXX",
                "autocomplete": "off",
                "class": "dashboard-code-input",
            }
        ),
        error_messages={
            "required": "Введите промокод.",
            "max_length": "Промокод состоит из 8 символов.",
        },
    )


class PromoCodeUploadForm(forms.Form):
    """Загрузка промокодов из xlsx-файла в админке."""

    file = forms.FileField(label="Файл .xlsx")

    def clean_file(self) -> UploadedFile:
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Нужен файл в формате .xlsx.")
        if file.content_type not in XLSX_CONTENT_TYPES:
            raise forms.ValidationError(
                "Файл не похож на настоящий .xlsx — проверьте расширение."
            )
        if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"Файл больше {MAX_UPLOAD_SIZE_MB} МБ — разбейте на "
                f"несколько файлов поменьше."
            )
        return file
