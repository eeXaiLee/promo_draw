from __future__ import annotations

from django.db import migrations

NEW_PRIZES = [
    "Сертификат OZON на 2000₽",
    "Яндекс Станция",
]


def deactivate_old_seed_new(apps, schema_editor) -> None:
    """Отключает весь прежний пул месячных призов (в т.ч. переименованные
    вручную через админку) и оставляет только те два, что реально указаны
    на сайте."""
    Prize = apps.get_model("giveaway", "Prize")
    Prize.objects.filter(kind="monthly", is_active=True).exclude(
        title__in=NEW_PRIZES
    ).update(is_active=False)
    Prize.objects.bulk_create(
        Prize(title=title, kind="monthly") for title in NEW_PRIZES
    )


def reactivate_old_remove_new(apps, schema_editor) -> None:
    Prize = apps.get_model("giveaway", "Prize")
    Prize.objects.filter(kind="monthly").exclude(
        title__in=NEW_PRIZES
    ).update(is_active=True)
    Prize.objects.filter(title__in=NEW_PRIZES, kind="monthly").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0009_seed_super_draw_task"),
    ]

    operations = [
        migrations.RunPython(
            deactivate_old_seed_new, reactivate_old_remove_new
        ),
    ]
