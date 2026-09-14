from __future__ import annotations

import math
import time

from django.core.cache import cache
from django.http import HttpRequest

RATE_LIMIT_WINDOW_SECONDS = 60

LOGIN_FAILS_WINDOW_SECONDS = 300
LOGIN_FAILS_THRESHOLD = 5
LOGIN_LOCKOUT_BASE_SECONDS = 300
LOGIN_LOCKOUT_MAX_SECONDS = 3600


def register_failed_login(email: str, ip: str) -> None:
    """Считает неудачные попытки входа для связки email+IP.

    После LOGIN_FAILS_THRESHOLD попыток за LOGIN_FAILS_WINDOW_SECONDS
    включает блокировку. Каждая следующая попытка удлиняет её —
    прогрессивная задержка вместо одной фиксированной паузы, как у брутфорса
    промокодов.
    """
    key = _fails_key(email, ip)
    added = cache.add(key, 1, timeout=LOGIN_FAILS_WINDOW_SECONDS)
    if added:
        count = 1
    else:
        try:
            count = cache.incr(key)
        except ValueError:
            cache.set(key, 1, timeout=LOGIN_FAILS_WINDOW_SECONDS)
            count = 1

    if count >= LOGIN_FAILS_THRESHOLD:
        extra = count - LOGIN_FAILS_THRESHOLD + 1
        lockout = min(
            LOGIN_LOCKOUT_BASE_SECONDS * extra, LOGIN_LOCKOUT_MAX_SECONDS
        )
        cache.set(_lock_key(email, ip), time.time() + lockout, timeout=lockout)


def clear_failed_logins(email: str, ip: str) -> None:
    """Сбрасывает счётчик неудач после успешного входа."""
    cache.delete(_fails_key(email, ip))
    cache.delete(_lock_key(email, ip))


def get_login_lock_message(email: str, ip: str) -> str | None:
    """Текст ошибки, если вход сейчас заблокирован, иначе None."""
    unlock_at = cache.get(_lock_key(email, ip))
    if unlock_at is None:
        return None

    seconds_left = int(unlock_at - time.time())
    if seconds_left <= 0:
        return None

    return (
        "Слишком много неверных попыток входа. "
        f"Попробуйте снова через {_format_remaining(seconds_left)}."
    )


def _fails_key(email: str, ip: str) -> str:
    return f"login:fails:{email}:{ip}"


def _lock_key(email: str, ip: str) -> str:
    return f"login:lock:{email}:{ip}"


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


def hit_rate_limit(key: str) -> bool:
    """Отмечает попытку по ключу.

    Возвращает True, если по этому ключу уже была попытка за последние
    RATE_LIMIT_WINDOW_SECONDS секунд — значит, лимит исчерпан и запрос
    нужно отклонить. Тот же кеш, что и у блокировки за неверные промокоды.
    """
    cache_key = f"throttle:{key}"
    added = cache.add(cache_key, True, timeout=RATE_LIMIT_WINDOW_SECONDS)
    return not added


NUM_TRUSTED_PROXIES = 2
"""Хостовый nginx (TLS) + контейнерный nginx."""


def get_client_ip(request: HttpRequest) -> str:
    """IP клиента — запись NUM_TRUSTED_PROXIES с конца X-Forwarded-For.

    Начало заголовка задаёт клиент и ему нельзя доверять, а в конец каждый
    наш прокси дописывает IP того, от кого реально принял соединение.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        parts = [part.strip() for part in forwarded_for.split(",")]
        if len(parts) >= NUM_TRUSTED_PROXIES:
            return parts[-NUM_TRUSTED_PROXIES]
    return request.META.get("REMOTE_ADDR", "")
