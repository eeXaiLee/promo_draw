from __future__ import annotations

import logging
import os
import smtplib
from typing import Any

from celery import Celery
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promo_draw.settings")

app = Celery("promo_draw")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 1
app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

app.conf.task_acks_late = True
app.conf.task_reject_on_worker_lost = True
app.conf.broker_transport_options = {"visibility_timeout": 300}

app.autodiscover_tasks()

# Общие настройки повтора для тасок отправки писем: растущая пауза между
# попытками и ограничение на число попыток
EMAIL_TASK_KWARGS = {
    "autoretry_for": (OSError, smtplib.SMTPException),
    "retry_backoff": True,
    "max_retries": 5,
}


def safe_delay(task: Any, *args: Any, **kwargs: Any) -> None:
    """Ставит таску в очередь, не давая сбою брокера сломать вызывающий код.

    Письмо не критично для результата операции (регистрация, погашение
    промокода) — падение Redis не должно рвать уже успешно выполненное
    действие с ошибкой 500. Логируем и идём дальше.
    """
    try:
        task.delay(*args, **kwargs)
    except Exception:
        logger.exception(
            "Не удалось поставить в очередь задачу %s",
            getattr(task, "name", task),
        )
