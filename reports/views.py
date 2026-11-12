import csv
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from residents.models import Resident
from rooms.models import Room
from billing.models import Charge, Payment

def index(request):
    total_capacity = Room.objects.aggregate(total=Sum('capacity'))['total'] or 0
    active_residents = Resident.objects.count()
    vacancies = max(0, total_capacity - active_residents)

    expected_charges = Charge.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    amount_collected = Payment.objects.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
    remaining_balance = max(Decimal('0.00'), expected_charges - amount_collected)

    today = timezone.localdate()
    due_soon_threshold = today + timedelta(days=7)

    charges = Charge.objects.all()
    paid_count = 0
    pending_count = 0
    due_soon_count = 0
    overdue_count = 0

    for charge in charges:
        if charge.status == 'PAID' or charge.pending_amount <= Decimal('0.00'):
            paid_count += 1
        elif charge.due_date < today:
            overdue_count += 1
        elif today <= charge.due_date <= due_soon_threshold:
            due_soon_count += 1
        else:
            pending_count += 1

    context = {
        'active_residents': active_residents,
        'total_capacity': total_capacity,
        'vacancies': vacancies,
        'expected_charges': expected_charges,
        'amount_collected': amount_collected,
        'remaining_balance': remaining_balance,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'due_soon_count': due_soon_count,
        'overdue_count': overdue_count,
    }
    return render(request, 'reports/index.html', context)

def residents_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="residents.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Phone', 'Room', 'Joining Date'])
    for r in Resident.objects.all().select_related('room'):
        room_name = f"Room {r.room.room_number}" if r.room else "Unassigned"
        writer.writerow([r.id, r.full_name, r.phone, room_name, r.joining_date])
    return response

def rooms_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rooms.csv"'
    writer = csv.writer(response)
    writer.writerow(['Room Number', 'Floor', 'Capacity', 'Occupants', 'Available Beds', 'Monthly Fee'])
    for room in Room.objects.all().prefetch_related('residents'):
        writer.writerow([
            room.room_number,
            room.floor,
            room.capacity,
            room.active_occupants,
            room.available_beds,
            room.monthly_fee
        ])
    return response
