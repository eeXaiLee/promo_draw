from __future__ import annotations

from django import forms


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
