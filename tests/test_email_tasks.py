from __future__ import annotations

from django.core import mail

from apps.accounts.models import User
from apps.accounts.tasks import (
    send_confirmation_email,
    send_password_reset_email,
)
from apps.promocodes.models import PromoCode
from apps.promocodes.tasks import send_promo_registered_email


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


def test_send_promo_registered_email_respects_notification_flag(
    complete_user: User,
) -> None:
    """Письмо о регистрации кода не уходит, если пользователь его отключил."""
    complete_user.notify_promo_registered = False
    complete_user.save(update_fields=["notify_promo_registered"])
    code = PromoCode.objects.create(code="MAIL0001", used_by=complete_user)

    send_promo_registered_email(code.pk)

    assert len(mail.outbox) == 0
