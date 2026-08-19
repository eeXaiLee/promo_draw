from __future__ import annotations

import secrets
import string
from typing import Any

from django.core.management.base import (
    BaseCommand,
    CommandError,
    CommandParser,
)

from apps.promocodes.models import PROMO_CODE_LENGTH, PromoCode

ALPHABET = string.ascii_uppercase + string.digits
BATCH_SIZE = 10_000
MAX_EMPTY_BATCHES = 5


def generate_code() -> str:
    return "".join(
        secrets.choice(ALPHABET) for _ in range(PROMO_CODE_LENGTH)
    )


class Command(BaseCommand):
    """Генерирует заданное количество промокодов и сохраняет их в базу."""

    help = "Генерирует промокоды: python manage.py generate_promo_codes --count 1500000"  # noqa: E501

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--count",
            type=int,
            required=True,
            help="Сколько промокодов сгенерировать.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        target: int = options["count"]
        created = 0
        empty_batches = 0

        while created < target:
            batch_size = min(BATCH_SIZE, target - created)
            codes = {generate_code() for _ in range(batch_size)}

            before = PromoCode.objects.count()
            PromoCode.objects.bulk_create(
                [PromoCode(code=code) for code in codes],
                ignore_conflicts=True,
            )
            added = PromoCode.objects.count() - before
            created += added

            if added > 0:
                empty_batches = 0
            else:
                empty_batches += 1
                if empty_batches >= MAX_EMPTY_BATCHES:
                    raise CommandError(
                        f"{MAX_EMPTY_BATCHES} пачек подряд не добавили ни "
                        "одного нового кода — похоже, свободных кодов "
                        f"почти не осталось. Создано {created} из {target}."
                    )

            self.stdout.write(f"Создано {created} из {target}")

        self.stdout.write(self.style.SUCCESS(f"Готово: {created} промокодов."))
