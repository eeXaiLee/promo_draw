from __future__ import annotations

import random

from django.db import transaction

from apps.promocodes.models import PromoCode

from .models import DRAW_PRIZE_COUNT, DailyDraw, Prize, Winner


def finalize_draw(draw: DailyDraw) -> list[Winner]:
    """Определяет победителей дня.

    Если розыгрыш уже финализирован, ничего не делает.
    Так ручной запуск из админки и автоматическая задача не мешают друг другу.

    Каждый погашенный за день код — отдельный билет: чем больше кодов
    погасил человек в этот день, тем выше его шанс выиграть.
    """
    with transaction.atomic():
        draw = DailyDraw.objects.select_for_update().get(pk=draw.pk)
        if draw.is_finalized:
            return []

        tickets = list(
            PromoCode.objects.filter(
                used_by__isnull=False, used_at__date=draw.date
            ).exclude(used_by__giveaway_win__isnull=False)
        )
        random.shuffle(tickets)

        prizes = list(Prize.objects.filter(is_active=True))
        random.shuffle(prizes)

        max_winners = min(DRAW_PRIZE_COUNT, len(prizes))
        seen_users: set[int] = set()
        winners: list[Winner] = []
        for promo_code in tickets:
            if len(winners) >= max_winners:
                break
            user_id = promo_code.used_by_id
            assert user_id is not None
            if user_id in seen_users:
                continue
            seen_users.add(user_id)
            winners.append(
                Winner.objects.create(
                    draw=draw,
                    prize=prizes[len(winners)],
                    user_id=user_id,
                    promo_code=promo_code,
                )
            )

        draw.is_finalized = True
        draw.save(update_fields=["is_finalized"])

    return winners
