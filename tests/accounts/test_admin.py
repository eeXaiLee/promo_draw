from __future__ import annotations

from apps.accounts.admin import UserAdmin


def test_user_admin_fieldsets_include_address_and_marketing_consent() -> None:
    """Поля, добавленные в модель миграциями 0004/0005, должны быть видны
    в карточке пользователя — иначе сотрудник не найдёт адрес доставки
    приза победителя ни в одном поле формы."""
    fields = {
        name for _, options in UserAdmin.fieldsets for name in options["fields"]
    }

    assert "address" in fields
    assert "marketing_consent" in fields
