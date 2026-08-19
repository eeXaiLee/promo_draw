from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    """Создаёт пользователей по email вместо username."""

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> User:
        if not email:
            raise ValueError("У пользователя должен быть email")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("email_confirmed", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("У суперпользователя должно быть is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "У суперпользователя должно быть is_superuser=True"
            )

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Пользователь личного кабинета, вход по email."""

    email = models.EmailField(unique=True)

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    patronymic = models.CharField(max_length=150, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    personal_data_consent = models.BooleanField(default=False)
    email_confirmed = models.BooleanField(default=False)
    notify_promo_registered = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self) -> str:
        return self.email

    def get_full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.patronymic]
        return " ".join(part for part in parts if part) or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email

    @property
    def public_display_name(self) -> str:
        """Имя Ф. — сокращённое имя для публичных страниц."""
        last_initial = f"{self.last_name[0]}." if self.last_name else ""
        return f"{self.first_name} {last_initial}".strip() or self.email

    @property
    def masked_phone(self) -> str:
        """Телефон вида +7 *** *** ХХ ХХ — видны только последние 4 цифры."""
        digits = "".join(ch for ch in self.phone if ch.isdigit())
        if len(digits) < 4:
            return ""
        if digits[0] == "8":
            digits = "7" + digits[1:]
        last_four = digits[-4:]
        return f"+{digits[0]} *** *** {last_four[:2]} {last_four[2:]}"

    @property
    def profile_is_complete(self) -> bool:
        """Заполнены ли обязательные поля профиля для ввода промокода."""
        return bool(
            self.first_name
            and self.last_name
            and self.birth_date
            and self.phone
        )
