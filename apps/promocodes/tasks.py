from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.accounts.models import User

from .models import PromoCode


@shared_task
def send_promo_registered_email(promo_code_id: int) -> None:
    """Письмо о погашении кода — только если пользователь не отключил его."""
    try:
        promo_code = PromoCode.objects.select_related("used_by").get(
            pk=promo_code_id
        )
    except PromoCode.DoesNotExist:
        return

    user: User | None = promo_code.used_by
    if user is None or not user.notify_promo_registered:
        return

    body = render_to_string(
        "promocodes/emails/promo_registered.txt", {"code": promo_code.code}
    )
    send_mail(
        subject="Промокод зарегистрирован — promo_draw",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
