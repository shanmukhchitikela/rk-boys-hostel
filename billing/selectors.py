from decimal import Decimal

from django.db.models import Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from .forms import BillingMonthFilterForm
from .models import MonthlyCharge
from .rules import status_expression


def annotated_charges(queryset=None, today=None):
    queryset = queryset if queryset is not None else MonthlyCharge.objects.all()
    amount_field = MonthlyCharge._meta.get_field("amount")
    return queryset.select_related("resident", "period").annotate(
        annotated_paid_amount=Coalesce(
            Sum("payments__amount"),
            Value(Decimal("0.00")),
            output_field=amount_field,
        )
    ).annotate(calculated_status=status_expression(today or timezone.localdate()))


def selected_billing_month(query_params):
    today = timezone.localdate()
    data = query_params.copy()
    if "year" not in data:
        data["year"] = str(today.year)
    if "month" not in data:
        data["month"] = str(today.month)
    form = BillingMonthFilterForm(data)
    if form.is_valid():
        return form.cleaned_data["year"], form.cleaned_data["month"], form
    return today.year, today.month, form


def monthly_billing_summary(year, month, today=None):
    charges = list(
        annotated_charges(today=today).filter(period__year=year, period__month=month)
    )
    counts = {
        MonthlyCharge.Status.PAID: 0,
        MonthlyCharge.Status.PENDING: 0,
        MonthlyCharge.Status.DUE_SOON: 0,
        MonthlyCharge.Status.OVERDUE: 0,
    }
    expected = Decimal("0.00")
    collected = Decimal("0.00")
    remaining = Decimal("0.00")
    for charge in charges:
        expected += charge.amount
        collected += charge.paid_amount
        remaining += charge.pending_amount
        counts[charge.status] += 1

    return {
        "expected_charges": expected,
        "amount_collected": collected,
        "remaining_balance": remaining,
        "paid_count": counts[MonthlyCharge.Status.PAID],
        "pending_count": counts[MonthlyCharge.Status.PENDING],
        "due_soon_count": counts[MonthlyCharge.Status.DUE_SOON],
        "overdue_count": counts[MonthlyCharge.Status.OVERDUE],
    }


def charge_roster_queryset(year, month, statuses):
    return annotated_charges().filter(
        period__year=year,
        period__month=month,
        calculated_status__in=statuses,
    ).order_by("resident__full_name", "pk")