from __future__ import annotations

import pytest

from apps.promocodes import rate_limit


def test_register_failed_attempt_survives_key_expiry_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ключ истекает между add и incr — отметка не падает ошибкой сервера."""
    user_id = 999999
    monkeypatch.setattr(rate_limit.cache, "add", lambda *args, **kwargs: False)

    rate_limit.register_failed_attempt(user_id)

    assert rate_limit.cache.get(rate_limit._fails_key(user_id)) == 1
    assert rate_limit.get_ban_message(user_id) is None
