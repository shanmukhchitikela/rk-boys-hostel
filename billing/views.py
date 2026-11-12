from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import Charge, Payment
from .forms import ChargeForm, PaymentForm

def charge_list(request):
    charges = Charge.objects.all().select_related('resident', 'resident__room').order_by('-due_date', '-id')

    query = request.GET.get('q', '').strip()
    year_filter = request.GET.get('year', '').strip()
    month_filter = request.GET.get('month', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) |
            Q(resident__phone__icontains=query) |
            Q(title__icontains=query)
        )
    if year_filter and year_filter.isdigit():
        charges = charges.filter(due_date__year=int(year_filter))
    if month_filter and month_filter.isdigit():
        charges = charges.filter(due_date__month=int(month_filter))
    if status_filter:
        charges = charges.filter(status=status_filter)

    paginator = Paginator(charges, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    month_choices = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    status_choices = Charge.STATUS_CHOICES

    context = {
        'charges': charges,
        'page_obj': page_obj,
        'query': query,
        'year_filter': year_filter,
        'month_filter': month_filter,
        'status_filter': status_filter,
        'month_choices': month_choices,
        'status_choices': status_choices,
    }
    return render(request, 'billing/charge_list.html', context)

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
    charge = get_object_or_404(Charge, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.charge = charge
            payment.save()

            # Automatically update charge status if paid in full
            if charge.pending_amount <= Decimal('0.00'):
                charge.status = 'PAID'
            elif charge.paid_amount > Decimal('0.00'):
                charge.status = 'PARTIAL'
            charge.save()

            messages.success(request, f"Payment of ₹{payment.amount_paid} recorded successfully!")
            return redirect('billing:charge_detail', pk=charge.pk)
    else:
        form = PaymentForm(initial={'charge': charge, 'amount_paid': charge.pending_amount})
    return render(request, 'billing/payment_form.html', {'form': form, 'charge': charge})

def payment_receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('charge', 'charge__resident', 'charge__resident__room'), pk=pk)
    charge = payment.charge
    resident = charge.resident
    room = resident.room
    context = {
        'payment': payment,
        'charge': charge,
        'resident': resident,
        'room': room,
    }
    return render(request, 'billing/payment_receipt.html', context)

def paid_residents(request):
    today = timezone.localdate()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    query = request.GET.get('q', '').strip()

    charges = Charge.objects.filter(status='PAID', due_date__year=year, due_date__month=month).select_related('resident')
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) |
            Q(resident__phone__icontains=query)
        )

    paginator = Paginator(charges, 20)
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

    charges = Charge.objects.exclude(status='PAID').select_related('resident')
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) |
            Q(resident__phone__icontains=query)
        )

    if status_filter == 'overdue':
        charges = charges.filter(due_date__lt=today)
    elif status_filter == 'due_soon':
        charges = charges.filter(due_date__gte=today, due_date__lte=due_soon_threshold)
    else:
        charges = charges.filter(Q(due_date__lt=today) | Q(due_date__lte=due_soon_threshold))

    paginator = Paginator(charges, 20)
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
    }
    return render(request, 'billing/attention_residents.html', context)
