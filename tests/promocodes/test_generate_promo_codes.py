from __future__ import annotations

from django.core.management import call_command

from apps.promocodes.models import PromoCode


def test_generate_promo_codes_creates_the_requested_count(db) -> None:
    """Команда реально создаёт запрошенное число кодов в базе."""
    call_command("generate_promo_codes", "--count", "50")

    assert PromoCode.objects.count() == 50
