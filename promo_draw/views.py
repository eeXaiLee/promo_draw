from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Стартовая страница — коротко про акцию и ссылки дальше."""
    return render(request, "home.html")
