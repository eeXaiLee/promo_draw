import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "promo_draw.settings")

app = Celery("promo_draw")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.broker_connection_retry_on_startup = True
app.conf.broker_connection_retry = True
app.conf.broker_connection_max_retries = 1
app.conf.beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"

app.autodiscover_tasks()
