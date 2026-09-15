from __future__ import annotations

import pytest
from django.contrib import admin as django_admin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from apps.accounts.models import User
from apps.promocodes.admin import PromoCodeAdmin
from apps.promocodes.models import PromoCode


def _staff_with_permissions(*codenames: str) -> User:
    """Сотрудник с указанными правами на PromoCode."""
    user = User.objects.create_user(
        email="staff@example.com", password="x", is_staff=True
    )
    content_type = ContentType.objects.get_for_model(PromoCode)
    permissions = Permission.objects.filter(
        content_type=content_type, codename__in=codenames
    )
    user.user_permissions.add(*permissions)
    return user


def test_upload_view_denies_staff_without_add_permission(db) -> None:
    """У сотрудника без права на добавление кодов нет доступа к загрузке."""
    viewer = _staff_with_permissions("view_promocode")
    request = RequestFactory().get("/admin/promocodes/promocode/upload/")
    request.user = viewer
    admin_instance = PromoCodeAdmin(PromoCode, django_admin.site)

    with pytest.raises(PermissionDenied):
        admin_instance.upload_view(request)


def test_upload_view_allows_staff_with_add_permission(db) -> None:
    """С правом на добавление кодов страница загрузки открывается."""
    uploader = _staff_with_permissions("view_promocode", "add_promocode")
    request = RequestFactory().get("/admin/promocodes/promocode/upload/")
    request.user = uploader
    admin_instance = PromoCodeAdmin(PromoCode, django_admin.site)

    response = admin_instance.upload_view(request)

    assert response.status_code == 200


def test_upload_view_shows_friendly_error_for_corrupt_file(db) -> None:
    """Файл, который не читается как xlsx, не роняет страницу в 500."""
    uploader = _staff_with_permissions("view_promocode", "add_promocode")
    upload = SimpleUploadedFile(
        "codes.xlsx",
        b"not actually a zip/xlsx file",
        content_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
    )
    request = RequestFactory().post(
        "/admin/promocodes/promocode/upload/", {"file": upload}
    )
    request.user = uploader
    admin_instance = PromoCodeAdmin(PromoCode, django_admin.site)

    response = admin_instance.upload_view(request)

    assert response.status_code == 200
    assert "не читается как xlsx" in response.content.decode()
