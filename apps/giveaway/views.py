from __future__ import annotations

import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .models import MonthlyDraw, Winner


@login_required
def winners_page(request: HttpRequest) -> HttpResponse:
    """Страница победителей по периодам — доступна только вошедшим."""
    draws = MonthlyDraw.objects.filter(is_finalized=True).order_by(
        "-period_start"
    )

    selected_draw = None
    date_param = request.GET.get("period")
    if date_param:
        try:
            selected_date = datetime.date.fromisoformat(date_param)
        except ValueError:
            selected_date = None
        if selected_date is not None:
            selected_draw = draws.filter(period_start=selected_date).first()
    if selected_draw is None:
        selected_draw = draws.first()

    winners: list[Winner] = []
    if selected_draw is not None:
        winners = list(
            Winner.objects.filter(draw=selected_draw).select_related(
                "prize", "user"
            )
        )

    return render(
        request,
        "giveaway/winners.html",
        {"draws": draws, "selected_draw": selected_draw, "winners": winners},
    )
