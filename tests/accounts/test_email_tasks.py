from __future__ import annotations

from django.core import mail

from apps.accounts.models import User
from apps.accounts.tasks import (
    send_confirmation_email,
    send_password_reset_email,
)


def test_send_confirmation_email(db) -> None:
    """Письмо подтверждения почты уходит на адрес нового пользователя."""
    user = User.objects.create_user(email="new@example.com", password="x")

    send_confirmation_email(user.pk)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new@example.com"]


def test_send_password_reset_email(db) -> None:
    """Письмо сброса пароля уходит на адрес пользователя."""
    user = User.objects.create_user(email="reset@example.com", password="x")

    send_password_reset_email(user.pk)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["reset@example.com"]
