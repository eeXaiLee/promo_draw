from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import (
    PasswordResetTokenGenerator,
    default_token_generator,
)
from django.core.exceptions import ValidationError
from django.http import HttpRequest

from .models import User
from .tasks import send_password_reset_email


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


class PasswordResetRequestForm(PasswordResetForm):
    """Запрос сброса пароля — письмо со ссылкой уходит через Celery."""

    def save(
        self,
        domain_override: str | None = None,
        subject_template_name: str = "registration/password_reset_subject.txt",
        email_template_name: str = "registration/password_reset_email.html",
        use_https: bool = False,
        token_generator: PasswordResetTokenGenerator = default_token_generator,
        from_email: str | None = None,
        request: HttpRequest | None = None,
        html_email_template_name: str | None = None,
        extra_email_context: dict[str, str] | None = None,
    ) -> None:
        for user in self.get_users(self.cleaned_data["email"]):
            send_password_reset_email.delay(user.pk)


class ProfileForm(forms.ModelForm):
    """Личные данные: обязательны для ввода промокода (кроме отчества)."""

    no_patronymic = forms.BooleanField(label="Нет отчества", required=False)

    class Meta:
        model = User
        fields = (
            "last_name",
            "first_name",
            "patronymic",
            "birth_date",
            "phone",
            "notify_promo_registered",
        )
        labels = {
            "last_name": "Фамилия",
            "first_name": "Имя",
            "patronymic": "Отчество",
            "birth_date": "Дата рождения",
            "phone": "Телефон",
            "notify_promo_registered": (
                "Присылать письмо при регистрации промокода"
            ),
        }
        widgets = {"birth_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["patronymic"].required = False
        had_no_patronymic = (
            self.instance.pk
            and self.instance.first_name
            and not self.instance.patronymic
        )
        if had_no_patronymic:
            self.fields["no_patronymic"].initial = True

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        if cleaned_data.get("no_patronymic"):
            cleaned_data["patronymic"] = ""
        elif not cleaned_data.get("patronymic"):
            self.add_error(
                "patronymic", "Укажите отчество или отметьте «нет отчества»."
            )
        return cleaned_data
