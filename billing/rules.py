from datetime import timedelta
from decimal import Decimal

from django.db.models import Case, CharField, F, Value, When
from django.utils import timezone

DUE_SOON_DAYS = 7


def status_for_balance(pending_amount, due_date, today=None):
    if pending_amount <= Decimal("0.00"):
        return "paid"

    today = today or timezone.localdate()
    if due_date < today:
        return "overdue"
    if due_date <= today + timedelta(days=DUE_SOON_DAYS):
        return "due_soon"
    return "pending"


def status_expression(today=None):
    today = today or timezone.localdate()
    return Case(
        When(annotated_paid_amount__gte=F("amount"), then=Value("paid")),
        When(due_date__lt=today, then=Value("overdue")),
        When(
            due_date__lte=today + timedelta(days=DUE_SOON_DAYS),
            then=Value("due_soon"),
        ),
        default=Value("pending"),
        output_field=CharField(),
    )