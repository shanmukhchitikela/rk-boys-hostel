import re
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Charge, Payment
from .forms import ChargeForm, PaymentForm
from rooms.models import Room
from rooms.utils import natural_room_key, natural_resident_key

def charge_list(request):
    all_charges = Charge.objects.all().select_related('resident', 'resident__room').order_by('-due_date', '-id')
    today = timezone.localdate()
    due_soon_threshold = today + timedelta(days=7)

    # Compute live tab counts across all charges
    count_all = all_charges.count()
    count_paid = 0
    count_pending = 0
    count_overdue = 0

    for c in all_charges:
        if c.status == 'PAID' or c.pending_amount <= Decimal('0.00'):
            count_paid += 1
        elif c.due_date < today or c.status == 'OVERDUE':
            count_overdue += 1
        else:
            count_pending += 1

    # Filters
    tab = request.GET.get('tab', 'all').strip().lower()
    query = request.GET.get('q', '').strip()
    room_filter = request.GET.get('room', '').strip()
    year_filter = request.GET.get('year', '').strip()
    month_filter = request.GET.get('month', '').strip()
    status_filter = request.GET.get('status', '').strip()
    due_filter = request.GET.get('due', '').strip()

    charges = all_charges

    # Apply tab filter
    if tab == 'paid':
        charges = charges.filter(Q(status='PAID'))
    elif tab == 'pending':
        charges = charges.filter(Q(status='PENDING') & Q(due_date__gte=today))
    elif tab == 'overdue':
        charges = charges.filter(Q(status='OVERDUE') | (Q(status__in=['PENDING', 'PARTIAL']) & Q(due_date__lt=today)))

    # Apply specific status filter if passed
    if status_filter:
        if status_filter == 'PAID':
            charges = charges.filter(status='PAID')
        elif status_filter == 'PENDING':
            charges = charges.filter(status='PENDING')
        elif status_filter == 'OVERDUE':
            charges = charges.filter(Q(status='OVERDUE') | (Q(status__in=['PENDING', 'PARTIAL']) & Q(due_date__lt=today)))
        elif status_filter == 'PARTIAL':
            charges = charges.filter(status='PARTIAL')

    if due_filter == 'soon':
        charges = charges.filter(status__in=['PENDING', 'PARTIAL'], due_date__gte=today, due_date__lte=due_soon_threshold)

    # Apply search query
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) |
            Q(resident__phone__icontains=query) |
            Q(resident__room__room_number__icontains=query) |
            Q(title__icontains=query)
        )

    # Apply room filter
    if room_filter:
        charges = charges.filter(resident__room_id=room_filter)

    # Apply year/month filter
    if year_filter and year_filter.isdigit():
        charges = charges.filter(due_date__year=int(year_filter))
    if month_filter and month_filter.isdigit():
        charges = charges.filter(due_date__month=int(month_filter))

    # Room-wise natural ascending numerical ordering (1, 2, ..., 10, 11)
    charges_list = list(charges)
    charges_list.sort(key=lambda c: natural_resident_key(c.resident))

    paginator = Paginator(charges_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Naturally sorted rooms for the dropdown
    all_rooms = sorted(Room.objects.all(), key=natural_room_key)

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    status_choices = Charge.STATUS_CHOICES

    context = {
        'charges': charges,
        'page_obj': page_obj,
        'tab': tab,
        'count_all': count_all,
        'count_paid': count_paid,
        'count_pending': count_pending,
        'count_overdue': count_overdue,
        'query': query,
        'room_filter': room_filter,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'status_filter': status_filter,
        'all_rooms': all_rooms,
        'month_choices': month_choices,
        'status_choices': status_choices,
        'today': today,
    }
    return render(request, 'billing/charge_list.html', context)

def payment_history(request):
    payments = Payment.objects.all().select_related('charge', 'charge__resident', 'charge__resident__room')

    method_filter = request.GET.get('method', '').strip()
    month_filter = request.GET.get('month', '').strip()
    year_filter = request.GET.get('year', '').strip()
    room_filter = request.GET.get('room', '').strip()
    sort = request.GET.get('sort', 'room').strip().lower()
    query = request.GET.get('q', '').strip()

    if method_filter:
        payments = payments.filter(payment_method__iexact=method_filter)

    if month_filter and month_filter.isdigit():
        payments = payments.filter(payment_date__month=int(month_filter))

    if year_filter and year_filter.isdigit():
        payments = payments.filter(payment_date__year=int(year_filter))

    if room_filter:
        payments = payments.filter(charge__resident__room_id=room_filter)

    if query:
        payments = payments.filter(
            Q(charge__resident__full_name__icontains=query) |
            Q(charge__resident__phone__icontains=query) |
            Q(charge__resident__room__room_number__icontains=query) |
            Q(reference__icontains=query) |
            Q(notes__icontains=query) |
            Q(charge__title__icontains=query)
        )

    # Sort payments: natural room order (1, 2, 3...) by default or by date
    payments_list = list(payments)
    if sort == 'date':
        payments_list.sort(key=lambda p: (p.payment_date, p.id), reverse=True)
    else:
        payments_list.sort(key=lambda p: natural_resident_key(p.charge.resident if p.charge else None))

    total_collected = sum(p.amount_paid for p in payments_list)
    total_count = len(payments_list)

    paginator = Paginator(payments_list, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Naturally sorted rooms for room filter dropdown
    all_rooms = sorted(Room.objects.all(), key=natural_room_key)

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    method_choices = [('Cash', 'Cash'), ('UPI', 'UPI'), ('Check', 'Check/Cheque')]

    context = {
        'page_obj': page_obj,
        'total_collected': total_collected,
        'total_count': total_count,
        'method_filter': method_filter,
        'month_filter': month_filter,
        'year_filter': year_filter,
        'room_filter': room_filter,
        'sort': sort,
        'query': query,
        'all_rooms': all_rooms,
        'month_choices': month_choices,
        'method_choices': method_choices,
    }
    return render(request, 'billing/payment_history.html', context)

def charge_create(request):
    if request.method == 'POST':
        form = ChargeForm(request.POST)
        if form.is_valid():
            charge = form.save()
            messages.success(request, f"Charge '{charge.title}' for {charge.resident.full_name} created successfully!")
            return redirect('billing:charge_list')
    else:
        form = ChargeForm()
    return render(request, 'billing/charge_form.html', {'form': form})

def charge_detail(request, pk):
    charge = get_object_or_404(Charge.objects.select_related('resident', 'resident__room'), pk=pk)
    return render(request, 'billing/charge_detail.html', {'charge': charge})

def payment_create(request, pk):
    charge = get_object_or_404(Charge.objects.select_related('resident', 'resident__room'), pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.charge = charge
            payment.save()

            # Automatically update charge status if paid in full
            charge.refresh_from_db()
            if charge.pending_amount <= Decimal('0.00'):
                charge.status = 'PAID'
            elif charge.paid_amount > Decimal('0.00'):
                charge.status = 'PARTIAL'
            charge.save()

            messages.success(request, f"Payment of ₹{payment.amount_paid} recorded successfully for {charge.resident.full_name}!")
            return redirect('billing:payment_receipt', pk=payment.pk)
    else:
        now_str = timezone.now().strftime('%Y-%m-%dT%H:%M')
        form = PaymentForm(initial={
            'amount_paid': charge.pending_amount,
            'payment_date': now_str,
            'payment_method': 'UPI'
        })
    return render(request, 'billing/payment_form.html', {'form': form, 'charge': charge})

def payment_receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('charge', 'charge__resident', 'charge__resident__room'), pk=pk)
    charge = payment.charge
    resident = charge.resident
    room = resident.room
    remaining_balance = charge.pending_amount

    context = {
        'payment': payment,
        'charge': charge,
        'resident': resident,
        'room': room,
        'remaining_balance': remaining_balance,
    }
    return render(request, 'billing/payment_receipt.html', context)

def paid_residents(request):
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    query = request.GET.get('q', '').strip()

    charges = Charge.objects.filter(status='PAID', due_date__year=year, due_date__month=month).select_related('resident', 'resident__room')
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) |
            Q(resident__phone__icontains=query)
        )

    charges_list = list(charges)
    charges_list.sort(key=lambda c: natural_resident_key(c.resident))

    paginator = Paginator(charges_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'year': year,
        'month': month,
        'query': query,
    }
    return render(request, 'billing/paid_residents.html', context)

def attention_residents(request):
    today = timezone.localdate()
    due_soon_threshold = today + timedelta(days=7)
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    charges = Charge.objects.exclude(status='PAID').select_related('resident', 'resident__room')
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) |
            Q(resident__phone__icontains=query)
        )

    if status_filter == 'overdue':
        charges = charges.filter(Q(status='OVERDUE') | Q(due_date__lt=today))
    elif status_filter == 'due_soon':
        charges = charges.filter(due_date__gte=today, due_date__lte=due_soon_threshold)
    else:
        charges = charges.filter(Q(status='OVERDUE') | Q(due_date__lt=today) | Q(due_date__lte=due_soon_threshold))

    charges_list = list(charges)
    charges_list.sort(key=lambda c: natural_resident_key(c.resident))

    paginator = Paginator(charges_list, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    attention_choices = [
        ('overdue', 'Overdue'),
        ('due_soon', 'Due soon')
    ]

    context = {
        'page_obj': page_obj,
        'year': year,
        'month': month,
        'query': query,
        'status_filter': status_filter,
        'attention_choices': attention_choices,
        'today': today,
    }
    return render(request, 'billing/attention_residents.html', context)
