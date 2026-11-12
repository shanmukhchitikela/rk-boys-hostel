from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Charge, Payment

@login_required
def charge_list(request):
    charges = Charge.objects.all()
    return render(request, 'billing/charge_list.html', {'charges': charges})

@login_required
def charge_create(request):
    return render(request, 'billing/charge_form.html')

@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'billing/payment_receipt.html', {'payment': payment})

@login_required
def paid_residents(request):
    return render(request, 'billing/paid_residents.html')

@login_required
def attention_residents(request):
    return render(request, 'billing/attention_residents.html')