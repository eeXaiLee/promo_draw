from __future__ import annotations

from django.contrib import admin as django_admin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory

from apps.accounts.models import User
from apps.giveaway.admin import MonthlyDrawAdmin
from apps.giveaway.models import MonthlyDraw


def _staff_with_permissions(*codenames: str) -> User:
    """Сотрудник с указанными правами на MonthlyDraw."""
    user = User.objects.create_user(
        email="staff@example.com", password="x", is_staff=True
    )
    content_type = ContentType.objects.get_for_model(MonthlyDraw)
    permissions = Permission.objects.filter(
        content_type=content_type, codename__in=codenames
    )
    user.user_permissions.add(*permissions)
    return user


def test_view_only_staff_has_no_finalize_action(db) -> None:
    """У сотрудника с правом только на просмотр нет ручного розыгрыша."""
    viewer = _staff_with_permissions("view_monthlydraw")
    request = RequestFactory().get("/admin/giveaway/monthlydraw/")
    request.user = viewer
    admin_instance = MonthlyDrawAdmin(MonthlyDraw, django_admin.site)

    actions = admin_instance.get_actions(request)

    assert "finalize_manually" not in actions


def test_staff_with_change_permission_has_finalize_action(db) -> None:
    """У сотрудника с правом на изменение действие доступно."""
    editor = _staff_with_permissions(
        "view_monthlydraw", "change_monthlydraw"
    )
    request = RequestFactory().get("/admin/giveaway/monthlydraw/")
    request.user = editor
    admin_instance = MonthlyDrawAdmin(MonthlyDraw, django_admin.site)

    actions = admin_instance.get_actions(request)

    assert "finalize_manually" in actions
