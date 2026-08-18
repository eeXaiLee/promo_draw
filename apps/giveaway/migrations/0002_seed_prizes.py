from __future__ import annotations

from django.db import migrations

PRIZES = [
    "Сертификат в магазин электроники, 3000 ₽",
    "Беспроводные наушники",
    "Портативная колонка Bluetooth",
    "Внешний аккумулятор (повербанк) 20000 мАч",
    "Сертификат в кафе/ресторан, 3000 ₽",
    "Термокружка/термобутылка",
    "Фитнес-браслет",
    "Сертификат в кино + попкорн на двоих",
    "Сертификат на доставку еды, 3000 ₽",
    "Электрический чайник",
    "Умные весы (напольные, с приложением)",
    "Плед с рукавами",
    "Сертификат в книжный магазин, 2000 ₽",
    "Вафельница/мини-мультиварка",
]


def seed_prizes(apps: migrations.state.ProjectState, schema_editor: object) -> None:
    Prize = apps.get_model("giveaway", "Prize")
    Prize.objects.bulk_create(Prize(title=title) for title in PRIZES)


def remove_prizes(apps: migrations.state.ProjectState, schema_editor: object) -> None:
    Prize = apps.get_model("giveaway", "Prize")
    Prize.objects.filter(title__in=PRIZES).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_prizes, remove_prizes),
    ]
