from decimal import Decimal

from django.conf import settings
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models import Q, Sum


def copy_legacy_advance_balances(apps, schema_editor):
    database = schema_editor.connection.alias
    Resident = apps.get_model("residents", "Resident")
    AdvanceTransaction = apps.get_model("billing", "AdvanceTransaction")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    staff_user = (
        User.objects.using(database)
        .filter(is_staff=True)
        .order_by("-is_superuser", "pk")
        .first()
    )

    for resident in Resident.objects.using(database).filter(advance_balance__gt=0).iterator():
        AdvanceTransaction.objects.using(database).create(
            resident_id=resident.pk,
            transaction_type="deposit",
            amount=resident.advance_balance,
            date=resident.joined_date,
            notes="Opening balance migrated from the resident profile.",
            recorded_by_id=staff_user.pk if staff_user else None,
        )


def restore_legacy_advance_balances(apps, schema_editor):
    database = schema_editor.connection.alias
    Resident = apps.get_model("residents", "Resident")
    AdvanceTransaction = apps.get_model("billing", "AdvanceTransaction")

    balances = (
        AdvanceTransaction.objects.using(database)
        .values("resident_id")
        .annotate(
            deposits=Sum("amount", filter=Q(transaction_type="deposit")),
            applied=Sum("amount", filter=Q(transaction_type="apply_to_rent")),
            refunds=Sum("amount", filter=Q(transaction_type="refund")),
        )
    )
    for totals in balances.iterator():
        resident = Resident.objects.using(database).get(pk=totals["resident_id"])
        resident.advance_balance = max(
            (totals["deposits"] or Decimal("0.00"))
            - (totals["applied"] or Decimal("0.00"))
            - (totals["refunds"] or Decimal("0.00")),
            Decimal("0.00"),
        )
        resident.save(using=database, update_fields=("advance_balance",))


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
        ("residents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="payment_mode",
            field=models.CharField(
                choices=[
                    ("cash", "Cash"),
                    ("bank_transfer", "Bank transfer"),
                    ("cheque", "Cheque"),
                    ("other", "Other"),
                    ("advance", "Advance"),
                ],
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="AdvanceTransaction",
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
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("deposit", "Deposit"),
                            ("apply_to_rent", "Apply to rent"),
                            ("refund", "Refund"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.01"))
                        ],
                    ),
                ),
                ("date", models.DateField(default=django.utils.timezone.localdate)),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "charge",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="advance_transactions",
                        to="billing.monthlycharge",
                    ),
                ),
                (
                    "payment",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="advance_transaction",
                        to="billing.payment",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recorded_advance_transactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "resident",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="advance_transactions",
                        to="residents.resident",
                    ),
                ),
            ],
            options={"ordering": ("-date", "-pk")},
        ),
        migrations.AddConstraint(
            model_name="advancetransaction",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gt", 0)),
                name="billing_advance_transaction_amount_positive",
            ),
        ),
        migrations.RunPython(
            copy_legacy_advance_balances, restore_legacy_advance_balances
        ),
    ]