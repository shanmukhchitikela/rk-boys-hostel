import calendar
import uuid
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from residents.models import Resident

from .models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment


class BillingMonthFilterForm(forms.Form):
    year = forms.IntegerField(
        min_value=1,
        max_value=9999,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 9999}),
    )
    month = forms.TypedChoiceField(
        choices=[(month, calendar.month_name[month]) for month in range(1, 13)],
        coerce=int,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class MonthlyChargeForm(forms.Form):
    resident = forms.ModelChoiceField(
        queryset=Resident.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    year = forms.IntegerField(
        min_value=1,
        max_value=9999,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 9999}),
    )
    month = forms.TypedChoiceField(
        choices=[(month, calendar.month_name[month]) for month in range(1, 13)],
        coerce=int,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"})
    )

    def __init__(self, *args, **kwargs):
        today = timezone.localdate()
        initial = kwargs.setdefault("initial", {})
        initial.setdefault("year", today.year)
        initial.setdefault("month", today.month)
        initial.setdefault("due_date", today)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        resident = cleaned_data.get("resident")
        year = cleaned_data.get("year")
        month = cleaned_data.get("month")
        if resident and year and month:
            period = BillingPeriod.objects.filter(year=year, month=month).first()
            if period and MonthlyCharge.objects.filter(
                resident=resident, period=period
            ).exists():
                raise ValidationError("A monthly charge already exists for this resident and period.")
        return cleaned_data

    @transaction.atomic
    def save(self):
        if not self.is_valid():
            raise ValueError("Cannot save an invalid monthly charge form.")
        resident = self.cleaned_data["resident"]
        period, _ = BillingPeriod.objects.get_or_create(
            year=self.cleaned_data["year"], month=self.cleaned_data["month"]
        )
        charge = MonthlyCharge(
            resident=resident,
            period=period,
            amount=resident.agreed_monthly_fee,
            due_date=self.cleaned_data["due_date"],
        )
        try:
            charge.save()
        except IntegrityError as error:
            raise ValidationError(
                "A monthly charge already exists for this resident and period."
            ) from error
        return charge


class PaymentForm(forms.Form):
    submission_key = forms.UUIDField(widget=forms.HiddenInput)
    amount = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "0.01", "step": "0.01"}),
    )
    payment_mode = forms.ChoiceField(
        choices=tuple(
            choice for choice in Payment.Mode.choices if choice[0] != Payment.Mode.ADVANCE
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    reference = forms.CharField(
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def __init__(self, *args, charge, **kwargs):
        self.charge = charge
        initial = kwargs.setdefault("initial", {})
        initial.setdefault("submission_key", uuid.uuid4())
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        submitted_key = self.cleaned_data.get("submission_key")
        if submitted_key and Payment.objects.filter(
            idempotency_key=submitted_key, charge=self.charge
        ).exists():
            return amount
        if amount > self.charge.pending_amount:
            raise ValidationError("Payment cannot exceed the remaining charge balance.")
        return amount


class AdvanceTransactionForm(forms.ModelForm):
    charge = forms.ModelChoiceField(
        queryset=MonthlyCharge.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = AdvanceTransaction
        fields = ("charge", "amount", "date", "reference", "notes")
        labels = {"date": "Transaction date"}
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "min": "0.01", "step": "0.01"}
            ),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "reference": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, resident, transaction_type, recorded_by, **kwargs):
        self.resident = resident
        self.transaction_type = transaction_type
        self.recorded_by = recorded_by
        super().__init__(*args, **kwargs)
        self.instance.resident = resident
        self.instance.transaction_type = transaction_type
        self.instance.recorded_by = recorded_by
        if transaction_type == AdvanceTransaction.Type.APPLY_TO_RENT:
            from .selectors import annotated_charges

            self.fields["charge"].required = True
            self.fields["charge"].queryset = annotated_charges().filter(
                resident=resident,
                annotated_paid_amount__lt=F("amount"),
            )
        else:
            self.fields.pop("charge")

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get("amount")
        if amount and self.transaction_type != AdvanceTransaction.Type.DEPOSIT:
            if amount > self.resident.advance_balance:
                self.add_error("amount", "Amount exceeds the resident's available advance balance.")
        charge = cleaned_data.get("charge")
        if charge and charge.resident_id != self.resident.pk:
            self.add_error("charge", "Choose a rent charge belonging to this resident.")
        if charge and amount and amount > charge.pending_amount:
            self.add_error("amount", "Advance application cannot exceed the remaining rent charge.")
        return cleaned_data

    def save(self, commit=True):
        transaction = super().save(commit=False)
        transaction.resident = self.resident
        transaction.transaction_type = self.transaction_type
        transaction.recorded_by = self.recorded_by
        transaction.charge = self.cleaned_data.get("charge")
        if commit:
            transaction.save()
        return transaction