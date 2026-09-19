from __future__ import annotations

import datetime

from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.promocodes.models import PromoRedemptionAttempt


def test_clean_old_attempts_removes_only_records_past_retention(db) -> None:
    """Старые записи журнала удаляются, свежие остаются нетронутыми."""
    user = User.objects.create_user(email="u@example.com", password="x")
    old = PromoRedemptionAttempt.objects.create(
        user=user, code_input="OLD00001", success=False
    )
    PromoRedemptionAttempt.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - datetime.timedelta(days=100)
    )
    recent = PromoRedemptionAttempt.objects.create(
        user=user, code_input="NEW00001", success=False
    )

    call_command("clean_old_attempts", "--days", "90")

    remaining_ids = set(
        PromoRedemptionAttempt.objects.values_list("pk", flat=True)
    )
    assert remaining_ids == {recent.pk}
