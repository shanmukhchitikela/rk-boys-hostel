import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from billing.models import Charge, Payment
from residents.models import Resident
from rooms.models import Room
from rooms.utils import natural_room_key, natural_resident_key


# ---------------------------------------------------------------------------
# Dashboard (index)
# ---------------------------------------------------------------------------

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
    paid_count = pending_count = due_soon_count = overdue_count = 0

    for charge in charges:
        if charge.status == 'PAID' or charge.pending_amount <= Decimal('0.00'):
            paid_count += 1
        elif charge.due_date < today or charge.status == 'OVERDUE':
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


# ---------------------------------------------------------------------------
# Drill-down report views (Strict Natural Numerical Order)
# ---------------------------------------------------------------------------

def vacancies_report(request):
    rooms = list(Room.objects.prefetch_related('residents').all())
    rooms.sort(key=natural_room_key)

    total_capacity = sum(r.capacity for r in rooms)
    total_occupied = sum(r.active_occupants for r in rooms)
    total_vacant = sum(r.available_beds for r in rooms)

    rooms_with_vacancy = [
        {
            'room': r,
            'capacity': r.capacity,
            'occupied': r.active_occupants,
            'available': r.available_beds,
            'residents': list(r.residents.all()),
        }
        for r in rooms if r.available_beds > 0
    ]

    all_rooms_roster = [
        {
            'room': r,
            'capacity': r.capacity,
            'occupied': r.active_occupants,
            'available': r.available_beds,
            'residents': list(r.residents.all()),
        }
        for r in rooms
    ]

    context = {
        'rooms_with_vacancy': rooms_with_vacancy,
        'all_rooms_roster': all_rooms_roster,
        'total_capacity': total_capacity,
        'total_occupied': total_occupied,
        'total_vacant': total_vacant,
        'vacant_rooms_count': len(rooms_with_vacancy),
        'total_rooms_count': len(rooms),
    }
    return render(request, 'reports/vacancies_report.html', context)


def expected_charges_report(request):
    today = timezone.localdate()
    month_filter = request.GET.get('month', '').strip()
    year_filter = request.GET.get('year', '').strip()

    charges = Charge.objects.select_related('resident', 'resident__room').all()

    if month_filter and month_filter.isdigit():
        charges = charges.filter(due_date__month=int(month_filter))
    if year_filter and year_filter.isdigit():
        charges = charges.filter(due_date__year=int(year_filter))

    charges_list = list(charges)
    charges_list.sort(key=lambda c: natural_resident_key(c.resident))

    total_expected = sum(c.amount for c in charges_list)
    total_paid = sum(c.paid_amount for c in charges_list)
    total_remaining = sum(c.pending_amount for c in charges_list)

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

    context = {
        'charges': charges_list,
        'total_expected': total_expected,
        'total_paid': total_paid,
        'total_remaining': total_remaining,
        'charges_count': len(charges_list),
        'month_filter': month_filter,
        'year_filter': year_filter,
        'month_choices': month_choices,
        'today': today,
    }
    return render(request, 'reports/expected_charges_report.html', context)


def collected_report(request):
    method_filter = request.GET.get('method', '').strip()
    month_filter = request.GET.get('month', '').strip()
    year_filter = request.GET.get('year', '').strip()
    query = request.GET.get('q', '').strip()

    payments = Payment.objects.select_related('charge', 'charge__resident', 'charge__resident__room').all()

    if method_filter:
        payments = payments.filter(payment_method__iexact=method_filter)
    if month_filter and month_filter.isdigit():
        payments = payments.filter(payment_date__month=int(month_filter))
    if year_filter and year_filter.isdigit():
        payments = payments.filter(payment_date__year=int(year_filter))
    if query:
        payments = payments.filter(
            Q(charge__resident__full_name__icontains=query) |
            Q(charge__resident__phone__icontains=query) |
            Q(charge__resident__room__room_number__icontains=query) |
            Q(reference__icontains=query)
        )

    payments_list = list(payments)
    payments_list.sort(key=lambda p: natural_resident_key(p.charge.resident if p.charge else None))

    total_collected = sum(p.amount_paid for p in payments_list)
    upi_total = sum(p.amount_paid for p in payments_list if p.payment_method == 'UPI')
    cash_total = sum(p.amount_paid for p in payments_list if p.payment_method == 'Cash')
    check_total = sum(p.amount_paid for p in payments_list if p.payment_method == 'Check')

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    method_choices = [('Cash', 'Cash'), ('UPI', 'UPI'), ('Check', 'Check/Cheque')]

    context = {
        'payments': payments_list,
        'total_collected': total_collected,
        'upi_total': upi_total,
        'cash_total': cash_total,
        'check_total': check_total,
        'payments_count': len(payments_list),
        'method_filter': method_filter,
        'month_filter': month_filter,
        'year_filter': year_filter,
        'query': query,
        'month_choices': month_choices,
        'method_choices': method_choices,
    }
    return render(request, 'reports/collected_report.html', context)


def balance_report(request):
    today = timezone.localdate()
    charges = list(
        Charge.objects.select_related('resident', 'resident__room')
        .exclude(status='PAID')
        .all()
    )
    charges = [c for c in charges if c.pending_amount > Decimal('0.00')]
    charges.sort(key=lambda c: natural_resident_key(c.resident))

    total_balance = sum(c.pending_amount for c in charges)
    overdue_count = sum(1 for c in charges if c.due_date < today or c.status == 'OVERDUE')
    pending_count = len(charges) - overdue_count

    context = {
        'charges': charges,
        'today': today,
        'total_balance': total_balance,
        'unpaid_count': len(charges),
        'overdue_count': overdue_count,
        'pending_count': pending_count,
    }
    return render(request, 'reports/balance_report.html', context)


# ---------------------------------------------------------------------------
# CSV exports
# ---------------------------------------------------------------------------

def residents_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="residents.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Phone', 'Room', 'Joining Date'])
    residents = list(Resident.objects.all().select_related('room'))
    residents.sort(key=natural_resident_key)
    for r in residents:
        room_name = f"Room {r.room.room_number}" if r.room else "Unassigned"
        writer.writerow([r.id, r.full_name, r.phone, room_name, r.joining_date])
    return response


def rooms_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rooms.csv"'
    writer = csv.writer(response)
    writer.writerow(['Room Number', 'Floor', 'Capacity', 'Occupants', 'Available Beds', 'Monthly Fee'])
    rooms = list(Room.objects.all().prefetch_related('residents'))
    rooms.sort(key=natural_room_key)
    for room in rooms:
        writer.writerow([
            room.room_number,
            room.floor,
            room.capacity,
            room.active_occupants,
            room.available_beds,
            room.monthly_fee
        ])
    return response


# ---------------------------------------------------------------------------
# Account Settings & Logout
# ---------------------------------------------------------------------------

@login_required
def account_settings(request):
    pw_form = None
    if request.method == 'POST':
        action = request.POST.get('action', '')

        if action == 'update_profile':
            user = request.user
            new_username = request.POST.get('username', '').strip()
            if new_username:
                user.username = new_username
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.save()
            messages.success(request, 'Profile details updated successfully.')
            return redirect('reports:account_settings')

        elif action == 'change_password':
            pw_form = PasswordChangeForm(request.user, request.POST)
            if pw_form.is_valid():
                user = pw_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Password changed successfully! You are still logged in.')
                return redirect('reports:account_settings')
            else:
                for field, errs in pw_form.errors.items():
                    for err in errs:
                        messages.error(request, f'{err}')

    if pw_form is None:
        pw_form = PasswordChangeForm(request.user)

    return render(request, 'reports/account_settings.html', {'pw_form': pw_form})


def logout_view(request):
    auth_logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('admin:login')
