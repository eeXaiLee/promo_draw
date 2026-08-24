from __future__ import annotations

import datetime

from apps.accounts.forms import ProfileForm
from apps.accounts.models import User


def test_profile_form_normalizes_phone(
    complete_user: User, profile_form_data: dict[str, object]
) -> None:
    """Телефон в сыром формате приводится к виду +79XXXXXXXXX."""
    form = ProfileForm(data=profile_form_data, instance=complete_user)

    assert form.is_valid(), form.errors
    assert form.cleaned_data["phone"] == "+79991234567"


def test_profile_form_rejects_garbage_phone(
    complete_user: User, profile_form_data: dict[str, object]
) -> None:
    """Телефон, из которого не собрать номер, форма не принимает."""
    data = profile_form_data | {"phone": "не телефон"}
    form = ProfileForm(data=data, instance=complete_user)

    assert not form.is_valid()
    assert "phone" in form.errors


def test_profile_form_rejects_future_birth_date(
    complete_user: User, profile_form_data: dict[str, object]
) -> None:
    """Дата рождения из будущего форма не принимает."""
    future_date = (
        datetime.date.today() + datetime.timedelta(days=1)
    ).isoformat()
    data = profile_form_data | {"birth_date": future_date}
    form = ProfileForm(data=data, instance=complete_user)

    assert not form.is_valid()
    assert "birth_date" in form.errors
