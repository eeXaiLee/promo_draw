from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

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
    """Стартовая страница — коротко про акцию и ссылки дальше."""
    return render(request, "home.html")


def stub_view(slug: str) -> Callable[..., HttpResponse]:
    """Заглушка для страницы, содержимое которой ещё не готово."""
    title, text = STUB_PAGES[slug]
    return TemplateView.as_view(
        template_name="stub.html",
        extra_context={"page_title": title, "page_text": text},
    )
