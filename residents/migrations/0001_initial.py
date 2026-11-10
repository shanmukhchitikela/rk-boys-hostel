import decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("rooms", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Resident",
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
                ("full_name", models.CharField(max_length=150)),
                ("phone", models.CharField(max_length=32)),
                ("joined_date", models.DateField()),
                (
                    "agreed_monthly_fee",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0.00"))
                        ],
                    ),
                ),
                (
                    "advance_balance",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0.00"))
                        ],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("exited", "Exited")],
                        default="active",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("full_name", "pk")},
        ),
        migrations.CreateModel(
            name="RoomAssignment",
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
                ("start_date", models.DateField(default=django.utils.timezone.localdate)),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "resident",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="room_assignments",
                        to="residents.resident",
                    ),
                ),
                (
                    "room",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments",
                        to="rooms.room",
                    ),
                ),
            ],
            options={"ordering": ("-start_date", "-pk")},
        ),
        migrations.AddConstraint(
            model_name="roomassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_date__isnull", True))
                | models.Q(("end_date__gte", models.F("start_date"))),
                name="residents_assignment_end_after_start",
            ),
        ),
    ]