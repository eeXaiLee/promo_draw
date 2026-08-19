from __future__ import annotations

from django import forms

XLSX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class PromoCodeForm(forms.Form):
    """Ввод промокода на странице погашения."""

    code = forms.CharField(
        label="Промокод",
        max_length=8,
        widget=forms.TextInput(
            attrs={"placeholder": "ABCD1234", "autocomplete": "off"}
        ),
        error_messages={
            "required": "Введите промокод.",
            "max_length": "Промокод состоит из 8 символов.",
        },
    )


class PromoCodeUploadForm(forms.Form):
    """Загрузка промокодов из xlsx-файла в админке."""

    file = forms.FileField(label="Файл .xlsx")

    def clean_file(self) -> object:
        file = self.cleaned_data["file"]
        if not file.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Нужен файл в формате .xlsx.")
        if file.content_type not in XLSX_CONTENT_TYPES:
            raise forms.ValidationError(
                "Файл не похож на настоящий .xlsx — проверьте расширение."
            )
        return file
