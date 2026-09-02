from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

TASK_NAME = "apps.giveaway.tasks.finalize_super_draw"
RUN_AT = datetime.datetime(
    2026, 12, 31, 0, 0, tzinfo=ZoneInfo("Europe/Moscow")
)


def create_periodic_task(
    apps: migrations.state.ProjectState, schema_editor: object
) -> None:
    ClockedSchedule = apps.get_model("django_celery_beat", "ClockedSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = ClockedSchedule.objects.get_or_create(clocked_time=RUN_AT)
    PeriodicTask.objects.get_or_create(
        task=TASK_NAME,
        defaults={
            "name": "Финализация супер-розыгрыша",
            "clocked": schedule,
            "one_off": True,
            "enabled": True,
        },
    )


def remove_periodic_task(
    apps: migrations.state.ProjectState, schema_editor: object
) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0008_monthly_periodic_task"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
