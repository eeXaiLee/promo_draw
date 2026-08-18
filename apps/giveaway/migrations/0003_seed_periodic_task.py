from __future__ import annotations

from django.db import migrations

TASK_NAME = "apps.giveaway.tasks.finalize_yesterday_draw"


def create_periodic_task(apps: migrations.state.ProjectState, schema_editor: object) -> None:
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="0",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="Europe/Moscow",
    )
    PeriodicTask.objects.get_or_create(
        task=TASK_NAME,
        defaults={
            "name": "Финализация розыгрыша за прошедшие сутки",
            "crontab": schedule,
            "enabled": True,
        },
    )


def remove_periodic_task(apps: migrations.state.ProjectState, schema_editor: object) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0002_seed_prizes"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
