"""
billing_utils.py
Shared helpers for monthly billing cycle due-date calculation,
dynamic status classification (Paid / Due Soon / Overdue / Pending),
and auto-sync of charge statuses on page load.

No external cron jobs required — call sync_resident_billing_statuses()
at the start of Dashboard, Billing Charges, and Reports views.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.utils import timezone

# Number of days before the due date that a charge is classified "Due Soon"
DUE_SOON_DAYS = 5


# ---------------------------------------------------------------------------
# Due-date calculation
# ---------------------------------------------------------------------------

def get_cycle_due_date(joining_date: date, year: int, month: int) -> date:
    """
    Return the monthly billing due date for a given (year, month),
    clamping the joining day to the last day of that month when needed.

    Example:
        joining_date = 2026-01-31, month = Feb (28 days)  → 2026-02-28
        joining_date = 2026-09-11, month = Nov             → 2026-11-11
    """
    day = joining_date.day
    max_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, max_day))


# ---------------------------------------------------------------------------
# Per-charge status classification (pure function — no DB writes)
# ---------------------------------------------------------------------------

def classify_charge(charge, today=None):
    """
    Classify a Charge instance into one of four display statuses.

    Returns a dict:
        display_status : 'Paid' | 'Due Soon' | 'Overdue' | 'Pending'
        status_code    : 'PAID' | 'DUE_SOON' | 'OVERDUE' | 'PENDING'
        days_overdue   : int  (> 0 when overdue, else 0)
        days_until_due : int  (>= 0 when upcoming, else None)
        badge_text     : human-readable string for the UI pill
    """
    if today is None:
        today = timezone.localdate()

    # Fully paid?
    if charge.pending_amount <= Decimal('0.00'):
        return {
            'display_status': 'Paid',
            'status_code': 'PAID',
            'days_overdue': 0,
            'days_until_due': None,
            'badge_text': 'Paid',
        }

    delta = (charge.due_date - today).days

    if delta < 0:
        days_late = abs(delta)
        return {
            'display_status': 'Overdue',
            'status_code': 'OVERDUE',
            'days_overdue': days_late,
            'days_until_due': None,
            'badge_text': f'Overdue by {days_late} day{"s" if days_late != 1 else ""}',
        }
    elif delta <= DUE_SOON_DAYS:
        label = 'Due Today' if delta == 0 else f'Due in {delta} day{"s" if delta != 1 else ""}'
        return {
            'display_status': 'Due Soon',
            'status_code': 'DUE_SOON',
            'days_overdue': 0,
            'days_until_due': delta,
            'badge_text': label,
        }
    else:
        return {
            'display_status': 'Pending',
            'status_code': 'PENDING',
            'days_overdue': 0,
            'days_until_due': delta,
            'badge_text': f'Due in {delta} days',
        }


# ---------------------------------------------------------------------------
# Auto-sync: auto-create missing monthly charges + update DB statuses
# ---------------------------------------------------------------------------

def sync_resident_billing_statuses():
    """
    1. For every active resident with a room: ensure a 'Monthly Rent' charge
       exists for the CURRENT billing month (auto-create if missing).
       Due date = joining day-of-month in the current month (clamped to month-end).

    2. For ALL existing charges: update DB status field based on today:
       - pending_amount <= 0  → PAID
       - due_date < today     → OVERDUE   (only if not already PAID)
       - otherwise            → PENDING   (only if not already PAID)
       Note: DUE_SOON is display-only; stored as PENDING in the DB.

    Returns: {'created': N, 'updated': N}
    """
    # Lazy imports to avoid circular imports at module load time
    from residents.models import Resident
    from billing.models import Charge

    today = timezone.localdate()
    year, month = today.year, today.month
    created = 0
    updated = 0

    # --- Step 1: Auto-create missing current-month charges ---
    active_residents = (
        Resident.objects
        .select_related('room')
        .filter(room__isnull=False)
    )

    for resident in active_residents:
        room = resident.room
        if not room or not room.monthly_fee:
            continue

        due_date = get_cycle_due_date(resident.joining_date, year, month)
        title_prefix = 'Monthly Rent'

        already_exists = Charge.objects.filter(
            resident=resident,
            due_date__year=year,
            due_date__month=month,
            title__startswith=title_prefix,
        ).exists()

        if not already_exists:
            Charge.objects.create(
                resident=resident,
                title=f"{title_prefix} - {due_date.strftime('%b %Y')}",
                amount=room.monthly_fee,
                due_date=due_date,
                status='PENDING',
            )
            created += 1

    # --- Step 2: Update DB status for all existing charges ---
    for charge in Charge.objects.select_related('resident').all():
        # Never downgrade an already-PAID charge
        if charge.status == 'PAID':
            continue

        info = classify_charge(charge, today)
        sc = info['status_code']

        if sc == 'PAID':
            if charge.status != 'PAID':
                Charge.objects.filter(pk=charge.pk).update(status='PAID')
                updated += 1
        elif sc == 'OVERDUE':
            if charge.status != 'OVERDUE':
                Charge.objects.filter(pk=charge.pk).update(status='OVERDUE')
                updated += 1
        else:
            # PENDING or DUE_SOON → both stored as PENDING
            if charge.status not in ('PENDING', 'PARTIAL'):
                Charge.objects.filter(pk=charge.pk).update(status='PENDING')
                updated += 1

    return {'created': created, 'updated': updated}
