from __future__ import annotations

from django.core import mail

from apps.accounts.models import User
from apps.promocodes.models import PromoCode
from apps.promocodes.tasks import send_promo_registered_email


def test_send_promo_registered_email_respects_notification_flag(
    complete_user: User,
) -> None:
    """Письмо о регистрации кода не уходит, если пользователь его отключил."""
    complete_user.notify_promo_registered = False
    complete_user.save(update_fields=["notify_promo_registered"])
    code = PromoCode.objects.create(code="MAIL0001", used_by=complete_user)

    send_promo_registered_email(code.pk)

    assert len(mail.outbox) == 0
