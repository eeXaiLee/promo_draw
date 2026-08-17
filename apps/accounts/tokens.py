from __future__ import annotations

from django.contrib.auth.tokens import PasswordResetTokenGenerator

from .models import User


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """Токен для ссылки подтверждения почты — одноразовый, как сброс пароля."""

    def _make_hash_value(self, user: User, timestamp: int) -> str:
        return f"{user.pk}{user.email}{user.email_confirmed}{timestamp}"


email_confirmation_token = EmailConfirmationTokenGenerator()
