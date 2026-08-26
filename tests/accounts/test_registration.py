from __future__ import annotations

from apps.accounts.forms import RegistrationForm

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
