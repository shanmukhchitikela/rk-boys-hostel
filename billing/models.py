import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone

from .rules import status_for_balance


class BillingPeriod(models.Model):
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(9999)]
    )
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )

    class Meta:
        ordering = ("-year", "-month")
        constraints = [
            models.UniqueConstraint(fields=("year", "month"), name="billing_period_year_month_unique"),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12),
                name="billing_period_month_in_range",
            ),
        ]

    def __str__(self):
        return f"{self.year:04d}-{self.month:02d}"


class MonthlyCharge(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PENDING = "pending", "Pending"
        DUE_SOON = "due_soon", "Due soon"
        OVERDUE = "overdue", "Overdue"

    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.PROTECT,
        related_name="monthly_charges",
    )
    period = models.ForeignKey(
        BillingPeriod,
        on_delete=models.PROTECT,
        related_name="charges",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-period__year", "-period__month", "resident__full_name")
        constraints = [
            models.UniqueConstraint(
                fields=("resident", "period"), name="billing_charge_resident_period_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0),
                name="billing_charge_amount_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.resident} - {self.period}"

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def paid_amount(self):
        annotated_amount = getattr(self, "annotated_paid_amount", None)
        if annotated_amount is not None:
            return annotated_amount
        return self.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    @property
    def pending_amount(self):
        return max(self.amount - self.paid_amount, Decimal("0.00"))

    @property
    def status(self):
        calculated_status = getattr(self, "calculated_status", None)
        if calculated_status is not None:
            return calculated_status
        return status_for_balance(self.pending_amount, self.due_date)

    @property
    def status_label(self):
        return self.Status(self.status).label


class Payment(models.Model):
    class Mode(models.TextChoices):
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        CHEQUE = "cheque", "Cheque"
        OTHER = "other", "Other"
        ADVANCE = "advance", "Advance"

    charge = models.ForeignKey(
        MonthlyCharge,
        on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    recorded_at = models.DateTimeField(default=timezone.now)
    payment_mode = models.CharField(max_length=20, choices=Mode.choices)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=40, unique=True, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ("-recorded_at", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="billing_payment_amount_positive"
            )
        ]

    def __str__(self):
        return self.receipt_number

    def clean(self):
        super().clean()
        if self.charge_id and self.amount is not None:
            outstanding = self.charge.pending_amount
            if self.pk:
                existing_amount = type(self).objects.filter(pk=self.pk).values_list(
                    "amount", flat=True
                ).first()
                if existing_amount:
                    outstanding += existing_amount
            if self.amount > outstanding:
                raise ValidationError(
                    {"amount": "Payment cannot exceed the remaining charge balance."}
                )

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Recorded payments are immutable; record a correction instead.")
        with transaction.atomic():
            MonthlyCharge.objects.select_for_update().get(pk=self.charge_id)
            if not self.receipt_number:
                self.receipt_number = f"RCT-{uuid.uuid4().hex.upper()}"
            self.full_clean()
            return super().save(*args, **kwargs)


class AdvanceTransaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        APPLY_TO_RENT = "apply_to_rent", "Apply to rent"
        REFUND = "refund", "Refund"

    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.PROTECT,
        related_name="advance_transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField(default=timezone.localdate)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_advance_transactions",
        blank=True,
        null=True,
    )
    charge = models.ForeignKey(
        MonthlyCharge,
        on_delete=models.PROTECT,
        related_name="advance_transactions",
        blank=True,
        null=True,
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.PROTECT,
        related_name="advance_transaction",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-date", "-pk")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="billing_advance_transaction_amount_positive",
            )
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.resident} - {self.amount}"

    @classmethod
    def balance_for(cls, resident_id):
        totals = cls.objects.filter(resident_id=resident_id).aggregate(
            deposits=models.Sum(
                "amount", filter=models.Q(transaction_type=cls.Type.DEPOSIT)
            ),
            applied=models.Sum(
                "amount", filter=models.Q(transaction_type=cls.Type.APPLY_TO_RENT)
            ),
            refunds=models.Sum(
                "amount", filter=models.Q(transaction_type=cls.Type.REFUND)
            ),
        )
        return (
            (totals["deposits"] or Decimal("0.00"))
            - (totals["applied"] or Decimal("0.00"))
            - (totals["refunds"] or Decimal("0.00"))
        )

    def clean(self):
        super().clean()
        if not self.recorded_by_id:
            raise ValidationError("A staff user is required to record this transaction.")

        if self.transaction_type == self.Type.APPLY_TO_RENT:
            if not self.charge_id:
                raise ValidationError({"charge": "Choose the rent charge to apply this advance to."})
            if self.resident_id and self.charge.resident_id != self.resident_id:
                raise ValidationError({"charge": "The rent charge must belong to this resident."})
            if self.charge_id:
                charge_balance = self.charge.pending_amount
                if self.payment_id:
                    charge_balance += self.payment.amount
                if self.amount > charge_balance:
                    raise ValidationError({"amount": "Advance application cannot exceed the remaining rent charge."})
        elif self.charge_id or self.payment_id:
            raise ValidationError("Only rent applications can be linked to a charge or payment.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Advance ledger entries are immutable; record a correcting transaction instead.")
        if not self.recorded_by_id:
            raise ValidationError({"recorded_by": "A staff user is required to record this transaction."})

        with transaction.atomic():
            from residents.models import Resident

            resident = Resident.objects.select_for_update().get(pk=self.resident_id)
            if self.transaction_type != self.Type.DEPOSIT:
                available_balance = type(self).balance_for(resident.pk)
                if self.amount > available_balance:
                    raise ValidationError({"amount": "Amount exceeds the resident's available advance balance."})

            if self.transaction_type == self.Type.APPLY_TO_RENT:
                charge = MonthlyCharge.objects.select_for_update().get(pk=self.charge_id)
                if charge.resident_id != resident.pk:
                    raise ValidationError({"charge": "The rent charge must belong to this resident."})
                payment = Payment(
                    charge=charge,
                    amount=self.amount,
                    payment_mode=Payment.Mode.ADVANCE,
                    reference=self.reference,
                    notes=self.notes,
                )
                payment.save()
                self.payment = payment
            elif self.charge_id or self.payment_id:
                raise ValidationError("Only rent applications can be linked to a charge or payment.")

            self.full_clean()
            return super().save(*args, **kwargs)