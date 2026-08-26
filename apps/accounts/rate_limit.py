from __future__ import annotations

from django.core.cache import cache
from django.http import HttpRequest

RATE_LIMIT_WINDOW_SECONDS = 60


def hit_rate_limit(key: str) -> bool:
    """Отмечает попытку по ключу.

    Возвращает True, если по этому ключу уже была попытка за последние
    RATE_LIMIT_WINDOW_SECONDS секунд — значит, лимит исчерпан и запрос
    нужно отклонить. Тот же кеш, что и у блокировки за неверные промокоды.
    """
    cache_key = f"throttle:{key}"
    added = cache.add(cache_key, True, timeout=RATE_LIMIT_WINDOW_SECONDS)
    return not added


def get_client_ip(request: HttpRequest) -> str:
    """IP клиента с учётом двух nginx перед приложением."""
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
