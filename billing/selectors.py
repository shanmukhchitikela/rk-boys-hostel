from django.db.models import Sum
from django.utils import timezone
from .models import Charge, Payment

def monthly_billing_summary():
    total_charges = Charge.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_payments = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or 0
    pending_dues = total_charges - total_payments
    return {
        'total_charges': total_charges,
        'total_payments': total_payments,
        'pending_dues': pending_dues,
    }

def selected_billing_month(request=None):
    now = timezone.now()
    return now.year, now.month