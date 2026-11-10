import django.db.models.deletion
from django.db import migrations, models


def validate_legacy_lengths(apps, schema_editor):
    database = schema_editor.connection.alias
    Resident = apps.get_model("residents", "Resident")
    for resident_id, full_name, phone in Resident.objects.using(database).values_list(
        "pk", "full_name", "phone"
    ).iterator():
        if len(full_name) > 100 or len(phone) > 15:
            raise RuntimeError(
                "Resident %s has a name or phone longer than the new field limit. "
                "Shorten that value before applying this migration."
                % resident_id
            )


def backfill_current_room_and_active_state(apps, schema_editor):
    database = schema_editor.connection.alias
    Resident = apps.get_model("residents", "Resident")
    RoomAssignment = apps.get_model("residents", "RoomAssignment")
    for resident in Resident.objects.using(database).all().iterator():
        assignment = (
            RoomAssignment.objects.using(database)
            .filter(resident_id=resident.pk, end_date__isnull=True)
            .order_by("-start_date", "-pk")
            .first()
        )
        Resident.objects.using(database).filter(pk=resident.pk).update(
            is_active=resident.status == "active",
            room_id=assignment.room_id if assignment else None,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_advance_transaction"),
        ("residents", "0002_remove_resident_advance_balance"),
    ]

    operations = [
        migrations.RunPython(validate_legacy_lengths, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="resident",
            old_name="joined_date",
            new_name="joining_date",
        ),
        migrations.AddField(
            model_name="resident",
            name="emergency_contact",
            field=models.CharField(default="", max_length=15),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="resident",
            name="id_proof_number",
            field=models.CharField(
                blank=True,
                help_text="Aadhaar/Govt ID",
                max_length=50,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="resident",
            name="room",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="residents",
                to="rooms.room",
            ),
        ),
        migrations.AddField(
            model_name="resident",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(
            backfill_current_room_and_active_state, migrations.RunPython.noop
        ),
        migrations.RemoveField(
            model_name="resident",
            name="status",
        ),
        migrations.AlterField(
            model_name="resident",
            name="full_name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="resident",
            name="phone",
            field=models.CharField(max_length=15),
        ),
    ]
