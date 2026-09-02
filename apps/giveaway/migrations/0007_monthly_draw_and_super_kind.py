from __future__ import annotations

import datetime

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

SUPER_PRIZES = [
    "Путешествие на 250 000 ₽",
    "Iphone 17 PRO",
    "Apple watch",
    "AirPods Pro 2",
]


def set_period_end(apps, schema_editor) -> None:
    MonthlyDraw = apps.get_model("giveaway", "MonthlyDraw")
    MonthlyDraw.objects.update(period_end=models.F("period_start"))


def seed_super_prizes(apps, schema_editor) -> None:
    Prize = apps.get_model("giveaway", "Prize")
    Prize.objects.bulk_create(
        Prize(title=title, kind="super") for title in SUPER_PRIZES
    )


def remove_super_prizes(apps, schema_editor) -> None:
    Prize = apps.get_model("giveaway", "Prize")
    Prize.objects.filter(title__in=SUPER_PRIZES, kind="super").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0006_winner_determined_by"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="DailyDraw", new_name="MonthlyDraw"
        ),
        migrations.RenameField(
            model_name="monthlydraw", old_name="date", new_name="period_start"
        ),
        migrations.AlterField(
            model_name="monthlydraw",
            name="period_start",
            field=models.DateField(),
        ),
        migrations.AddField(
            model_name="monthlydraw",
            name="period_end",
            field=models.DateField(default=datetime.date(1970, 1, 1)),
            preserve_default=False,
        ),
        migrations.RunPython(set_period_end, migrations.RunPython.noop),
        migrations.AddField(
            model_name="monthlydraw",
            name="kind",
            field=models.CharField(
                choices=[
                    ("monthly", "Ежемесячный"),
                    ("super", "Супер-розыгрыш"),
                ],
                default="monthly",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="monthlydraw",
            name="prize_count",
            field=models.PositiveSmallIntegerField(default=2),
        ),
        migrations.AlterModelOptions(
            name="monthlydraw",
            options={
                "ordering": ["-period_start"],
                "verbose_name": "розыгрыш",
                "verbose_name_plural": "розыгрыши",
            },
        ),
        migrations.AddConstraint(
            model_name="monthlydraw",
            constraint=models.UniqueConstraint(
                fields=("period_start", "period_end", "kind"),
                name="one_draw_per_period_kind",
            ),
        ),
        migrations.AddField(
            model_name="prize",
            name="kind",
            field=models.CharField(
                choices=[
                    ("monthly", "Ежемесячный"),
                    ("super", "Супер-розыгрыш"),
                ],
                default="monthly",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="winner",
            name="kind",
            field=models.CharField(
                choices=[
                    ("monthly", "Ежемесячный"),
                    ("super", "Супер-розыгрыш"),
                ],
                default="monthly",
                max_length=10,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="winner",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="giveaway_wins",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="winner",
            constraint=models.UniqueConstraint(
                fields=("user", "kind"), name="one_win_per_kind"
            ),
        ),
        migrations.RunPython(seed_super_prizes, remove_super_prizes),
    ]
