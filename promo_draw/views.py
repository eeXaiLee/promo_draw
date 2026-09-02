from __future__ import annotations

import datetime
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import date as format_date
from django.views.generic import TemplateView

from apps.giveaway.models import DrawKind, MonthlyDraw

STUB_PAGES: dict[str, tuple[str, str]] = {
    "about": (
        "О нас",
        "«Эскимос Лаб» производит мороженое и проводит акцию "
        "«10 месяцев побед». Подробный рассказ о компании "
        "появится здесь позже.",
    ),
    "contacts": (
        "Контакты",
        "Раздел в разработке. Актуальные контакты для связи "
        "появятся здесь позже.",
    ),
    "promotions": (
        "Акции",
        "Здесь будут собраны все текущие и прошедшие акции "
        "бренда. Раздел в разработке.",
    ),
    "personal-data": (
        "Обработка персональных данных",
        "Политика обработки персональных данных появится здесь позже.",
    ),
    "user-agreement": (
        "Пользовательское соглашение",
        "Текст пользовательского соглашения появится здесь позже.",
    ),
    "loyalty-rules": (
        "Правила программы лояльности",
        "Правила программы лояльности появятся здесь позже.",
    ),
    "loyalty-terms": (
        "Условия сервиса лояльности",
        "Условия сервиса лояльности появятся здесь позже.",
    ),
    "organizer": (
        "Реквизиты организатора акции",
        "Юридические реквизиты организатора акции появятся здесь позже.",
    ),
    "cookie-policy": (
        "Политика использования cookie",
        "Политика использования cookie-файлов появится здесь позже.",
    ),
}


def home(request: HttpRequest) -> HttpResponse:
    """Стартовая страница — коротко про акцию и ссылки дальше.

    Блок победителей показывает все 12 месяцев акции: там, где розыгрыш
    уже прошёл — реальные победители, где ещё нет — пусто.
    """
    draws_by_month = {
        draw.period_end.month: draw
        for draw in (
            MonthlyDraw.objects.filter(kind=DrawKind.MONTHLY, is_finalized=True)
            .order_by("period_end")
            .prefetch_related(
                "winners__prize", "winners__user", "winners__promo_code"
            )
        )
    }
    winners_months = [
        {
            "label": format_date(datetime.date(2026, month, 1), "F"),
            "draw": draws_by_month.get(month),
        }
        for month in range(1, 13)
    ]
    winners_active_index = next(
        (i for i, month in enumerate(winners_months) if month["draw"]), 0
    )
    return render(
        request,
        "home.html",
        {
            "winners_months": winners_months,
            "winners_active_index": winners_active_index,
        },
    )


def stub_view(slug: str) -> Callable[..., HttpResponse]:
    """Заглушка для страницы, содержимое которой ещё не готово."""
    title, text = STUB_PAGES[slug]
    return TemplateView.as_view(
        template_name="stub.html",
        extra_context={"page_title": title, "page_text": text},
    )
