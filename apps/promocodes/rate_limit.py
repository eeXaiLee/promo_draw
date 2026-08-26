from __future__ import annotations

import math
import time

from django.core.cache import cache

FAILS_WINDOW_SECONDS = 60
FAILS_THRESHOLD = 3
BAN_SECONDS = 300


def register_failed_attempt(user_id: int) -> None:
    """Считает неудачные попытки подряд и банит при превышении лимита."""
    key = _fails_key(user_id)
    added = cache.add(key, 1, timeout=FAILS_WINDOW_SECONDS)
    if added:
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            # Ключ истёк между add и incr — окно уже закрылось, отсчёт заново.
            cache.set(key, 1, timeout=FAILS_WINDOW_SECONDS)
            count = 1

    if count >= FAILS_THRESHOLD:
        cache.set(
            _ban_key(user_id), time.time() + BAN_SECONDS, timeout=BAN_SECONDS
        )


def get_ban_message(user_id: int) -> str | None:
    """Текст ошибки, если пользователь сейчас забанен, иначе None."""
    ban_until = cache.get(_ban_key(user_id))
    if ban_until is None:
        return None

    seconds_left = int(ban_until - time.time())
    if seconds_left <= 0:
        return None

    return (
        "Слишком много неверных попыток подряд. "
        f"Попробуйте снова через {_format_remaining(seconds_left)}."
    )


def _fails_key(user_id: int) -> str:
    return f"promo:fails:{user_id}"


def _ban_key(user_id: int) -> str:
    return f"promo:ban:{user_id}"


def _format_remaining(seconds: int) -> str:
    if seconds <= 60:
        return "меньше минуты"
    minutes = math.ceil(seconds / 60)
    return f"{minutes} {_pluralize_minutes(minutes)}"


def _pluralize_minutes(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "минуту"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "минуты"
    return "минут"
