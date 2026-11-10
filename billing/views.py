import calendar
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from auditlog.models import HostelSettings
from core.permissions import role_required
from residents.models import RoomAssignment

from .forms import BillingMonthFilterForm, MonthlyChargeForm, PaymentForm
from .models import BillingPeriod, MonthlyCharge, Payment
from .selectors import annotated_charges, charge_roster_queryset, selected_billing_month


def _add_validation_error(form, error):
    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            target = field if field in form.fields else None
            for message in errors:
                form.add_error(target, message)
    else:
        form.add_error(None, error)


@role_required("Owner", "Manager", "Warden")
def charge_list(request):
    charges = annotated_charges()
    query = request.GET.get("q", "").strip()
    year = request.GET.get("year", "").strip()
    month = request.GET.get("month", "").strip()
    status_filter = request.GET.get("status", "")

    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query)
            | Q(resident__phone__icontains=query)
            | Q(payments__receipt_number__icontains=query)
        )
    if year.isdigit():
        charges = charges.filter(period__year=int(year))
    if month.isdigit() and 1 <= int(month) <= 12:
        charges = charges.filter(period__month=int(month))
    if status_filter in MonthlyCharge.Status.values:
        charges = charges.filter(calculated_status=status_filter)

    charges = charges.distinct().order_by(
        "-period__year", "-period__month", "resident__full_name", "pk"
    )
    page_obj = Paginator(charges, 25).get_page(request.GET.get("page"))
    periods = BillingPeriod.objects.all()
    return render(
        request,
        "billing/charge_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "year_filter": year,
            "month_filter": month,
            "status_filter": status_filter,
            "status_choices": MonthlyCharge.Status.choices,
            "month_choices": [(month, calendar.month_name[month]) for month in range(1, 13)],
            "periods": periods,
        },
    )


@role_required("Owner", "Manager", "Warden")
def paid_resident_roster(request):
    year, month, month_form = selected_billing_month(request.GET)
    query = request.GET.get("q", "").strip()
    charges = charge_roster_queryset(year, month, (MonthlyCharge.Status.PAID,))
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) | Q(resident__phone__icontains=query)
        )
    page_obj = Paginator(charges, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "billing/paid_residents.html",
        {"page_obj": page_obj, "year": year, "month": month, "month_form": month_form, "query": query},
    )


@role_required("Owner", "Manager", "Warden")
def attention_residents(request):
    year, month, month_form = selected_billing_month(request.GET)
    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    statuses = (
        (status_filter,)
        if status_filter in (MonthlyCharge.Status.DUE_SOON, MonthlyCharge.Status.OVERDUE)
        else (MonthlyCharge.Status.DUE_SOON, MonthlyCharge.Status.OVERDUE)
    )
    charges = charge_roster_queryset(year, month, statuses)
    if query:
        charges = charges.filter(
            Q(resident__full_name__icontains=query) | Q(resident__phone__icontains=query)
        )
    if status_filter in statuses:
        charges = charges.filter(calculated_status=status_filter)
    page_obj = Paginator(charges, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "billing/attention_residents.html",
        {
            "page_obj": page_obj,
            "year": year,
            "month": month,
            "month_form": month_form,
            "query": query,
            "status_filter": status_filter,
            "attention_choices": (
                (MonthlyCharge.Status.DUE_SOON, MonthlyCharge.Status.DUE_SOON.label),
                (MonthlyCharge.Status.OVERDUE, MonthlyCharge.Status.OVERDUE.label),
            ),
        },
    )


@role_required("Owner", "Manager", "Warden")
@require_http_methods(["GET", "POST"])
def charge_create(request):
    form = MonthlyChargeForm(data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            charge = form.save()
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            messages.success(request, "Monthly charge created.")
            return redirect("billing:charge_detail", pk=charge.pk)
    return render(request, "billing/charge_form.html", {"form": form})


@role_required("Owner", "Manager", "Warden")
def charge_detail(request, pk):
    charge = get_object_or_404(
        annotated_charges().prefetch_related("payments"), pk=pk
    )
    return render(request, "billing/charge_detail.html", {"charge": charge})


@role_required("Owner", "Manager", "Warden")
def payment_receipt(request, pk):
    payment = get_object_or_404(
        Payment.objects.select_related(
            "charge__resident", "charge__period"
        ),
        pk=pk,
    )
    period = payment.charge.period
    period_start = date(period.year, period.month, 1)
    period_end = date(
        period.year, period.month, calendar.monthrange(period.year, period.month)[1]
    )
    room_assignment = (
        RoomAssignment.objects.filter(
            resident=payment.charge.resident,
            start_date__lte=period_end,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=period_start))
        .select_related("room")
        .order_by("-start_date")
        .first()
    )
    hostel_settings = HostelSettings.get_solo()
    return render(
        request,
        "billing/payment_receipt.html",
        {
            "payment": payment,
            "charge": payment.charge,
            "resident": payment.charge.resident,
            "room": room_assignment.room if room_assignment else None,
            "receipt_recorded_at": timezone.localtime(payment.recorded_at),
            "hostel_settings": hostel_settings,
        },
    )


@role_required("Owner", "Manager", "Warden")
@require_http_methods(["GET", "POST"])
def payment_create(request, charge_pk):
    charge = get_object_or_404(MonthlyCharge.objects.select_related("resident", "period"), pk=charge_pk)
    if charge.pending_amount <= Decimal("0.00"):
        messages.info(request, "This charge is already paid.")
        return redirect("billing:charge_detail", pk=charge.pk)

    form = PaymentForm(
        data=request.POST if request.method == "POST" else None,
        charge=charge,
    )
    if request.method == "POST" and form.is_valid():
        submission_key = form.cleaned_data["submission_key"]
        previous_payment = Payment.objects.filter(idempotency_key=submission_key).first()
        if previous_payment:
            if previous_payment.charge_id != charge.pk:
                form.add_error(None, "This submission key was already used for another charge.")
                return render(
                    request,
                    "billing/payment_form.html",
                    {"form": form, "charge": charge},
                )
            messages.info(request, f"This payment was already recorded as {previous_payment.receipt_number}.")
            return redirect("billing:charge_detail", pk=previous_payment.charge_id)

        try:
            with transaction.atomic():
                locked_charge = MonthlyCharge.objects.select_for_update().get(pk=charge.pk)
                previous_payment = Payment.objects.filter(
                    idempotency_key=submission_key
                ).first()
                if previous_payment:
                    payment = previous_payment
                    created = False
                else:
                    payment, created = Payment.objects.get_or_create(
                        idempotency_key=submission_key,
                        defaults={
                            "charge": locked_charge,
                            "amount": form.cleaned_data["amount"],
                            "payment_mode": form.cleaned_data["payment_mode"],
                            "reference": form.cleaned_data["reference"],
                            "notes": form.cleaned_data["notes"],
                        },
                    )
        except ValidationError as error:
            _add_validation_error(form, error)
        else:
            if created:
                messages.success(request, f"Payment recorded. Receipt {payment.receipt_number}.")
            else:
                messages.info(request, f"This payment was already recorded as {payment.receipt_number}.")
            return redirect("billing:charge_detail", pk=payment.charge_id)

    return render(
        request,
        "billing/payment_form.html",
        {"form": form, "charge": charge},
    )