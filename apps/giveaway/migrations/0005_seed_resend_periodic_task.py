from __future__ import annotations

from django.db import migrations

TASK_NAME = "apps.giveaway.tasks.resend_pending_winner_emails"


def create_periodic_task(
    apps: migrations.state.ProjectState, schema_editor: object
) -> None:
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=15, period="minutes"
    )
    PeriodicTask.objects.get_or_create(
        task=TASK_NAME,
        defaults={
            "name": "Досылка писем победителям",
            "interval": schedule,
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
        ("giveaway", "0004_winner_email_sent_at"),
    ]

    operations = [
        migrations.RunPython(create_periodic_task, remove_periodic_task),
    ]
