from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User
from .tokens import email_confirmation_token


@shared_task
def send_confirmation_email(user_id: int) -> None:
    """Отправляет письмо со ссылкой подтверждения почты."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_confirmation_token.make_token(user)
    confirm_path = reverse("accounts:confirm_email", args=[uid, token])
    confirm_url = f"{settings.SITE_URL}{confirm_path}"

    body = render_to_string(
        "accounts/emails/confirm_email.txt", {"confirm_url": confirm_url}
    )
    send_mail(
        subject="Подтверждение регистрации — promo_draw",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


@shared_task
def send_password_reset_email(user_id: int) -> None:
    """Отправляет письмо со ссылкой сброса пароля."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_path = reverse(
        "accounts:password_reset_confirm", args=[uid, token]
    )
    reset_url = f"{settings.SITE_URL}{reset_path}"

    body = render_to_string(
        "accounts/emails/password_reset.txt", {"reset_url": reset_url}
    )
    send_mail(
        subject="Сброс пароля — promo_draw",
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
