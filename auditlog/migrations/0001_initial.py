import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.contrib.contenttypes.models


def create_default_hostel_settings(apps, schema_editor):
    HostelSettings = apps.get_model("auditlog", "HostelSettings")
    HostelSettings.objects.using(schema_editor.connection.alias).get_or_create(
        singleton_key="main",
        defaults={
            "hostel_name": getattr(settings, "HOSTEL_NAME", "Hostel Desk"),
            "address": getattr(settings, "HOSTEL_ADDRESS", ""),
            "phone_numbers": getattr(settings, "HOSTEL_PHONE", ""),
        },
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HostelSettings",
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
                ("singleton_key", models.CharField(default="main", editable=False, max_length=16, unique=True)),
                ("hostel_name", models.CharField(default="Hostel Desk", max_length=160)),
                ("address", models.TextField(blank=True)),
                ("phone_numbers", models.TextField(blank=True)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("receipt_text", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "hostel settings",
                "verbose_name_plural": "hostel settings",
            },
        ),
        migrations.CreateModel(
            name="AuditEvent",
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
                ("action", models.CharField(max_length=80)),
                ("object_id", models.CharField(max_length=64)),
                ("object_label", models.CharField(max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="contenttypes.contenttype",
                    ),
                ),
            ],
            options={"ordering": ("-timestamp", "-pk")},
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["content_type", "object_id"], name="auditlog_au_content_79f0ab_idx"),
        ),
        migrations.AddIndex(
            model_name="auditevent",
            index=models.Index(fields=["timestamp"], name="auditlog_au_timesta_495d96_idx"),
        ),
        migrations.RunPython(create_default_hostel_settings, migrations.RunPython.noop),
    ]