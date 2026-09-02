from __future__ import annotations

from django.db import migrations

OLD_TASK_NAME = "apps.giveaway.tasks.finalize_yesterday_draw"
NEW_TASK_NAME = "apps.giveaway.tasks.finalize_monthly_draw"


def update_periodic_task(
    apps: migrations.state.ProjectState, schema_editor: object
) -> None:
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="0",
        day_of_week="*",
        day_of_month="10",
        month_of_year="*",
        timezone="Europe/Moscow",
    )
    PeriodicTask.objects.filter(task=OLD_TASK_NAME).update(
        task=NEW_TASK_NAME,
        name="Финализация ежемесячного розыгрыша",
        crontab=schedule,
    )


def revert_periodic_task(
    apps: migrations.state.ProjectState, schema_editor: object
) -> None:
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
    PeriodicTask.objects.filter(task=NEW_TASK_NAME).update(
        task=OLD_TASK_NAME,
        name="Финализация розыгрыша за прошедшие сутки",
        crontab=schedule,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0007_monthly_draw_and_super_kind"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(update_periodic_task, revert_periodic_task),
    ]
