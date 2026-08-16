from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class RegistrationForm(forms.ModelForm):
    """Регистрация: email, пароль дважды, согласие на обработку данных."""

    password1 = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Повторите пароль", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "personal_data_consent")
        labels = {
            "email": "Email",
            "personal_data_consent": (
                "Даю согласие на обработку персональных данных"
            ),
        }

    def clean_personal_data_consent(self) -> bool:
        consent = self.cleaned_data.get("personal_data_consent")
        if not consent:
            raise ValidationError(
                "Без согласия на обработку персональных данных "
                "регистрация невозможна."
            )
        return bool(consent)

    def clean_password2(self) -> str | None:
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Пароли не совпадают.")
        return password2

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        password = cleaned_data.get("password2")
        if password:
            try:
                validate_password(password)
            except ValidationError as error:
                self.add_error("password1", error)
        return cleaned_data

    def save(self, commit: bool = True) -> User:
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
