from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from billing.selectors import monthly_billing_summary, selected_billing_month
from core.permissions import role_required
from residents.models import Resident
from rooms.models import Room


@role_required("Owner", "Manager", "Warden")
def dashboard(request):
    year, month, month_form = selected_billing_month(request.GET)
    room_rows = Room.objects.annotate(
        current_occupants=Count(
            "assignments", filter=Q(assignments__end_date__isnull=True)
        )
    ).values_list("capacity", "current_occupants")
    room_totals = list(room_rows)
    summary = monthly_billing_summary(year, month, today=timezone.localdate())
    summary.update(
        {
            "active_residents": Resident.objects.filter(is_active=True).count(),
            "total_capacity": sum(capacity for capacity, _ in room_totals),
            "vacancies": sum(
                max(capacity - occupants, 0) for capacity, occupants in room_totals
            ),
            "year": year,
            "month": month,
        }
    )
    return render(
        request,
        "core/dashboard.html",
        {"summary": summary, "month_form": month_form},
    )