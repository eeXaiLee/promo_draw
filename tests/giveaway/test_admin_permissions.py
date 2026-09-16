from __future__ import annotations

import datetime

from django.contrib import admin as django_admin
from django.contrib import messages
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from apps.accounts.models import User
from apps.giveaway.admin import MonthlyDrawAdmin
from apps.giveaway.models import MonthlyDraw, Prize
from apps.giveaway.services import moscow_day_bounds
from apps.promocodes.models import PromoCode


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
    editor = _staff_with_permissions("view_monthlydraw", "change_monthlydraw")
    request = RequestFactory().get("/admin/giveaway/monthlydraw/")
    request.user = editor
    admin_instance = MonthlyDrawAdmin(MonthlyDraw, django_admin.site)

    actions = admin_instance.get_actions(request)

    assert "finalize_manually" in actions


def test_finalize_manually_warns_when_prizes_run_short(db) -> None:
    """Нехватка активных призов не проходит для сотрудника незамеченной."""
    editor = _staff_with_permissions("view_monthlydraw", "change_monthlydraw")
    Prize.objects.update(is_active=False)
    Prize.objects.create(title="Единственный приз")
    date = datetime.date(2030, 5, 9)
    draw = MonthlyDraw.objects.create(
        period_start=date, period_end=date, prize_count=2
    )
    day_start, _ = moscow_day_bounds(date)
    ticket_owner = User.objects.create_user(email="p@example.com", password="x")
    PromoCode.objects.create(
        code="CODE0001",
        used_by=ticket_owner,
        used_at=day_start + datetime.timedelta(hours=12),
    )

    request = RequestFactory().post("/admin/giveaway/monthlydraw/")
    request.user = editor

    def _get_response(request: HttpRequest) -> HttpResponse:
        return HttpResponse()

    SessionMiddleware(_get_response).process_request(request)
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    admin_instance = MonthlyDrawAdmin(MonthlyDraw, django_admin.site)

    admin_instance.finalize_manually(
        request, MonthlyDraw.objects.filter(pk=draw.pk)
    )

    warnings = [
        m
        for m in request._messages  # type: ignore[attr-defined]
        if m.level == messages.WARNING
    ]
    assert len(warnings) == 1
    assert "Проверьте пул активных призов" in warnings[0].message
