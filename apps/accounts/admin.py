from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import User


class UserCreationFormForAdmin(UserCreationForm):
    """Форма создания пользователя в админке — логин по email."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)


class UserChangeFormForAdmin(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Админка пользователя: логин по email, без username."""

    add_form = UserCreationFormForAdmin
    form = UserChangeFormForAdmin
    model = User

    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "email_confirmed",
        "date_joined",
    )
    list_filter = ("is_staff", "is_active", "email_confirmed")
    search_fields = ("email", "first_name", "last_name", "phone")
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Личные данные",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "patronymic",
                    "birth_date",
                    "phone",
                )
            },
        ),
        (
            "Согласия и уведомления",
            {
                "fields": (
                    "personal_data_consent",
                    "email_confirmed",
                    "notify_promo_registered",
                )
            },
        ),
        (
            "Права доступа",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Даты", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
