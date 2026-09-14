from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import authenticate
from django.test import Client
from django.urls import reverse

from apps.accounts.forms import RegistrationForm
from apps.accounts.models import User

VALID_DATA = {
    "email": "newuser@example.com",
    "password1": "Kj9#mPqR2vXz88Lw",
    "password2": "Kj9#mPqR2vXz88Lw",
    "personal_data_consent": "on",
}


def test_registration_form_valid(db) -> None:
    """С корректными данными форма проходит валидацию."""
    form = RegistrationForm(data=VALID_DATA)

    assert form.is_valid(), form.errors


def test_registration_form_rejects_password_mismatch(db) -> None:
    """Если пароли не совпадают, форма не проходит валидацию."""
    data = VALID_DATA | {"password2": "другой-пароль-123"}
    form = RegistrationForm(data=data)

    assert not form.is_valid()
    assert "password2" in form.errors


def test_registration_form_requires_consent(db) -> None:
    """Без согласия на обработку данных форма не проходит валидацию."""
    data = VALID_DATA | {"personal_data_consent": ""}
    form = RegistrationForm(data=data)

    assert not form.is_valid()
    assert "personal_data_consent" in form.errors


def test_registration_form_rejects_weak_password(db) -> None:
    """Слишком простой пароль форма не принимает."""
    data = VALID_DATA | {"password1": "12345678", "password2": "12345678"}
    form = RegistrationForm(data=data)

    assert not form.is_valid()
    assert "password1" in form.errors


def test_registration_form_lowercases_email(db) -> None:
    """«Ivan@Mail.ru» и «ivan@mail.ru» — один и тот же адрес."""
    data = VALID_DATA | {"email": "NewUser@Example.com"}
    form = RegistrationForm(data=data)

    assert form.is_valid(), form.errors
    assert form.cleaned_data["email"] == "newuser@example.com"


def test_registration_form_rejects_duplicate_email_different_case(
    db,
) -> None:
    """Тот же email в другом регистре — уже занят, а не новый аккаунт."""
    User.objects.create_user(email="ivan@mail.ru", password="testpass123")
    data = VALID_DATA | {"email": "Ivan@Mail.ru"}

    form = RegistrationForm(data=data)

    assert not form.is_valid()
    assert "email" in form.errors


def test_registration_succeeds_even_if_email_task_fails(
    client: Client, db: None
) -> None:
    """Падение брокера при постановке письма не должно рвать регистрацию."""
    with patch(
        "apps.accounts.views.send_confirmation_email.delay",
        side_effect=OSError("broker unavailable"),
    ):
        client.post(reverse("accounts:register"), VALID_DATA)

    assert User.objects.filter(email=VALID_DATA["email"]).exists()


def test_login_is_case_insensitive(db) -> None:
    """Вход с другим регистром email, чем при регистрации, работает."""
    User.objects.create_user(email="ivan@mail.ru", password="testpass123")

    user = authenticate(username="Ivan@Mail.ru", password="testpass123")

    assert user is not None
    assert user.email == "ivan@mail.ru"
