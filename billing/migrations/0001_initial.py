import decimal
import uuid

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("residents", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingPeriod",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "year",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(9999),
                        ]
                    ),
                ),
                (
                    "month",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ]
                    ),
                ),
            ],
            options={"ordering": ("-year", "-month")},
        ),
        migrations.CreateModel(
            name="MonthlyCharge",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0.00"))
                        ],
                    ),
                ),
                ("due_date", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "period",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="charges",
                        to="billing.billingperiod",
                    ),
                ),
                (
                    "resident",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="monthly_charges",
                        to="residents.resident",
                    ),
                ),
            ],
            options={"ordering": ("-period__year", "-period__month", "resident__full_name")},
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0.01"))
                        ],
                    ),
                ),
                ("recorded_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "payment_mode",
                    models.CharField(
                        choices=[
                            ("cash", "Cash"),
                            ("bank_transfer", "Bank transfer"),
                            ("cheque", "Cheque"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("receipt_number", models.CharField(editable=False, max_length=40, unique=True)),
                ("idempotency_key", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "charge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="billing.monthlycharge",
                    ),
                ),
            ],
            options={"ordering": ("-recorded_at", "-pk")},
        ),
        migrations.AddConstraint(
            model_name="billingperiod",
            constraint=models.UniqueConstraint(
                fields=("year", "month"), name="billing_period_year_month_unique"
            ),
        ),
        migrations.AddConstraint(
            model_name="billingperiod",
            constraint=models.CheckConstraint(
                condition=models.Q(("month__gte", 1), ("month__lte", 12)),
                name="billing_period_month_in_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="monthlycharge",
            constraint=models.UniqueConstraint(
                fields=("resident", "period"),
                name="billing_charge_resident_period_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="monthlycharge",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gte", 0)),
                name="billing_charge_amount_nonnegative",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gt", 0)),
                name="billing_payment_amount_positive",
            ),
        ),
    ]