from __future__ import annotations

from django.core.management import call_command

from apps.promocodes.models import PromoCode


def test_generate_promo_codes_creates_the_requested_count(db) -> None:
    """Команда реально создаёт запрошенное число кодов в базе."""
    call_command("generate_promo_codes", "--count", "50")

    assert PromoCode.objects.count() == 50


def test_generate_promo_codes_avoids_ambiguous_characters(db) -> None:
    """Ни O/0, ни I/1, ни S/5 не используются — человек не должен
    гадать, какую половину пары напечатали на палочке от мороженого."""
    call_command("generate_promo_codes", "--count", "200")

    codes = PromoCode.objects.values_list("code", flat=True)
    assert not any(set(code) & set("OIS015") for code in codes)
