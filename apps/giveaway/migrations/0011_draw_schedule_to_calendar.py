from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

from django.db import migrations

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

MONTHLY_TASK_NAME = "apps.giveaway.tasks.finalize_monthly_draw"
SUPER_TASK_NAME = "apps.giveaway.tasks.finalize_super_draw"
CATCH_UP_TASK_NAME = "apps.giveaway.tasks.catch_up_monthly_draws"

# Крон месячного розыгрыша ограничен этой датой (день после последнего
# розыгрыша акции, 9 декабря) — сам по себе он бессрочный, а после конца
# акции создавать новые месячные розыгрыши уже не должен ни при каких
# условиях. Плюс к этому — проверка в коде (get_or_create_monthly_draw).
MONTHLY_TASK_EXPIRES = datetime.datetime(2026, 12, 10, tzinfo=MOSCOW_TZ)

OLD_SUPER_DRAW_RUN_AT = datetime.datetime(2026, 12, 31, 0, 0, tzinfo=MOSCOW_TZ)
NEW_SUPER_DRAW_RUN_AT = datetime.datetime(2027, 1, 1, 0, 0, tzinfo=MOSCOW_TZ)


def move_monthly_draw_to_9th(apps, schema_editor) -> None:
    """Розыгрыш переезжает с 10-го числа 00:00 на 9-е число 21:00 — тексты
    на сайте всегда обещали «каждое 9-е число», крон стоял неверно."""
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="21",
        day_of_week="*",
        day_of_month="9",
        month_of_year="*",
        timezone="Europe/Moscow",
    )
    PeriodicTask.objects.filter(task=MONTHLY_TASK_NAME).update(
        crontab=schedule, expires=MONTHLY_TASK_EXPIRES
    )


def revert_monthly_draw_to_10th(apps, schema_editor) -> None:
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
    PeriodicTask.objects.filter(task=MONTHLY_TASK_NAME).update(
        crontab=schedule, expires=None
    )


def move_super_draw_to_new_year(apps, schema_editor) -> None:
    """Билеты супер-розыгрыша принимаются по 31.12 включительно — запуск
    ровно в 00:00 31.12 отрезал бы от розыгрыша весь последний день окна."""
    ClockedSchedule = apps.get_model("django_celery_beat", "ClockedSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = ClockedSchedule.objects.get_or_create(
        clocked_time=NEW_SUPER_DRAW_RUN_AT
    )
    PeriodicTask.objects.filter(task=SUPER_TASK_NAME).update(clocked=schedule)


def revert_super_draw_to_old_date(apps, schema_editor) -> None:
    ClockedSchedule = apps.get_model("django_celery_beat", "ClockedSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = ClockedSchedule.objects.get_or_create(
        clocked_time=OLD_SUPER_DRAW_RUN_AT
    )
    PeriodicTask.objects.filter(task=SUPER_TASK_NAME).update(clocked=schedule)


def create_catch_up_task(apps, schema_editor) -> None:
    """Подстраховка на случай простоя ровно в момент розыгрыша — раз в
    30 минут дозакрывает любой период, который почему-то не закрылся сам."""
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    schedule, _ = IntervalSchedule.objects.get_or_create(
        every=30, period="minutes"
    )
    PeriodicTask.objects.get_or_create(
        task=CATCH_UP_TASK_NAME,
        defaults={
            "name": "Дозакрытие пропущенных розыгрышей",
            "interval": schedule,
            "enabled": True,
        },
    )


def remove_catch_up_task(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task=CATCH_UP_TASK_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("giveaway", "0010_real_monthly_prizes"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(
            move_monthly_draw_to_9th, revert_monthly_draw_to_10th
        ),
        migrations.RunPython(
            move_super_draw_to_new_year, revert_super_draw_to_old_date
        ),
        migrations.RunPython(create_catch_up_task, remove_catch_up_task),
    ]
