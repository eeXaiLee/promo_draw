from __future__ import annotations

import datetime
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.utils import timezone

from apps.promocodes.models import PromoRedemptionAttempt

DEFAULT_RETENTION_DAYS = 90


class Command(BaseCommand):
    """Удаляет старые записи журнала попыток погашения промокода."""

    help = (
        "Удаляет записи PromoRedemptionAttempt старше N дней: "
        "python manage.py clean_old_attempts --days 90"
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=DEFAULT_RETENTION_DAYS,
            help=(
                "Хранить записи не старше стольких дней "
                f"(по умолчанию {DEFAULT_RETENTION_DAYS})."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, сколько записей удалится, не удалять.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        days: int = options["days"]
        dry_run: bool = options["dry_run"]
        cutoff = timezone.now() - datetime.timedelta(days=days)

        queryset = PromoRedemptionAttempt.objects.filter(created_at__lt=cutoff)
        count = queryset.count()

        if dry_run:
            self.stdout.write(
                f"Найдено {count} записей старше {days} дн. "
                "Ничего не удалено (--dry-run)."
            )
            return

        queryset.delete()
        self.stdout.write(
            self.style.SUCCESS(f"Удалено {count} записей старше {days} дн.")
        )
