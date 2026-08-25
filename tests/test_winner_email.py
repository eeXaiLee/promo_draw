from __future__ import annotations

import datetime

from django.core import mail
from django.utils import timezone

from apps.accounts.models import User
from apps.giveaway.models import DailyDraw, Prize, Winner
from apps.giveaway.tasks import resend_pending_winner_emails, send_winner_email
from apps.promocodes.models import PromoCode


def _create_winner(
    user: User, prize: Prize, draw: DailyDraw, code: str
) -> Winner:
    """Создаёт победителя с уже погашенным промокодом."""
    promo_code = PromoCode.objects.create(
        code=code, used_by=user, used_at=timezone.now()
    )
    return Winner.objects.create(
        draw=draw, prize=prize, user=user, promo_code=promo_code
    )


def test_send_winner_email_marks_sent_at(
    complete_user: User, two_prizes: list[Prize]
) -> None:
    """После успешной отправки у победителя проставляется email_sent_at."""
    draw = DailyDraw.objects.create(date=datetime.date(2030, 2, 1))
    winner = _create_winner(complete_user, two_prizes[0], draw, "WINR0001")

    send_winner_email(winner.pk)

    winner.refresh_from_db()
    assert winner.email_sent_at is not None
    assert len(mail.outbox) == 1


def test_resend_pending_winner_emails_skips_already_sent(
    two_prizes: list[Prize],
) -> None:
    """Досылка трогает только победителей без email_sent_at."""
    draw = DailyDraw.objects.create(date=datetime.date(2030, 2, 1))
    already_sent_user = User.objects.create_user(
        email="sent@example.com", password="testpass123"
    )
    pending_user = User.objects.create_user(
        email="pending@example.com", password="testpass123"
    )
    already_sent = _create_winner(
        already_sent_user, two_prizes[0], draw, "WINR0002"
    )
    already_sent.email_sent_at = timezone.now()
    already_sent.save(update_fields=["email_sent_at"])
    pending = _create_winner(pending_user, two_prizes[1], draw, "WINR0003")

    resend_pending_winner_emails()

    pending.refresh_from_db()
    assert pending.email_sent_at is not None
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [pending_user.email]
