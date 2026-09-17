from __future__ import annotations

from django.db import migrations


def backfill_snapshot(apps, schema_editor) -> None:
    """Заполняет снимок ФИО/email/телефона по уже существующим победам —
    до этой миграции такого снимка не было, а аккаунт мог быть удалён
    раньше, чем мы начали его сохранять."""
    Winner = apps.get_model("giveaway", "Winner")
    for winner in Winner.objects.select_related("user").filter(
        user__isnull=False, winner_full_name=""
    ):
        user = winner.user
        parts = [user.last_name, user.first_name, user.patronymic]
        full_name = " ".join(part for part in parts if part) or user.email
        winner.winner_full_name = full_name
        winner.winner_email = user.email
        winner.winner_phone = user.phone
        winner.save(
            update_fields=["winner_full_name", "winner_email", "winner_phone"]
        )


def noop_reverse(apps, schema_editor) -> None:
    """Обратно снимок не стираем — это чистый бэкфилл, откат схемы (0012)
    и так уберёт сами поля."""


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0012_winner_winner_email_winner_winner_full_name_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_snapshot, noop_reverse),
    ]
