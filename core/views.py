from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from billing.selectors import monthly_billing_summary, selected_billing_month
from residents.models import Resident
from rooms.models import Room

@login_required
def dashboard(request):
    year, month = selected_billing_month(request)
    summary = monthly_billing_summary()
    
    context = {
        'total_residents': Resident.objects.filter(is_active=True).count(),
        'total_rooms': Room.objects.count(),
        'billing_summary': summary,
        'selected_year': year,
        'selected_month': month,
    }
    return render(request, 'core/dashboard.html', context)