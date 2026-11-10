from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from billing.models import AdvanceTransaction, Payment
from residents.models import Resident, RoomAssignment
from rooms.models import Room

from .context import get_current_actor
from .models import AuditEvent, HostelSettings

TRACKED_FIELDS = {
    Resident: (
        "full_name",
        "phone",
        "emergency_contact",
        "id_proof_number",
        "joining_date",
        "agreed_monthly_fee",
        "room_id",
        "is_active",
    ),
    Room: ("room_number", "floor", "capacity", "monthly_fee", "notes"),
    RoomAssignment: ("resident_id", "room_id", "start_date", "end_date"),
    HostelSettings: ("hostel_name", "address", "phone_numbers", "email", "receipt_text"),
}


@receiver(pre_save)
def capture_previous_audit_fields(sender, instance, using, **kwargs):
    tracked_fields = TRACKED_FIELDS.get(sender)
    if not tracked_fields:
        return
    previous_values = None
    if instance.pk:
        previous_values = (
            sender.objects.using(using)
            .filter(pk=instance.pk)
            .values(*tracked_fields)
            .first()
        )
    instance._audit_previous_values = previous_values


def _action_for(sender, instance, created):
    if sender is Resident:
        previous = getattr(instance, "_audit_previous_values", None) or {}
        if created:
            return "resident_created"
        if previous.get("is_active") and not instance.is_active:
            return "resident_exited"
        return "resident_updated"

    if sender is Room:
        return "room_created" if created else "room_updated"

    if sender is RoomAssignment:
        previous = getattr(instance, "_audit_previous_values", None) or {}
        if created:
            return "resident_assigned_to_room"
        if previous.get("end_date") is None and instance.end_date is not None:
            return "room_assignment_closed"
        return "room_assignment_updated"

    if sender is Payment:
        return "payment_recorded"

    if sender is AdvanceTransaction:
        return {
            AdvanceTransaction.Type.DEPOSIT: "advance_deposit_recorded",
            AdvanceTransaction.Type.APPLY_TO_RENT: "advance_applied_to_rent",
            AdvanceTransaction.Type.REFUND: "advance_refund_recorded",
        }.get(instance.transaction_type, "advance_transaction_recorded")

    if sender is HostelSettings:
        return "hostel_settings_created" if created else "hostel_settings_updated"

    return None


@receiver(post_save)
def record_audit_event(sender, instance, created, using, **kwargs):
    if sender not in (*TRACKED_FIELDS, Payment, AdvanceTransaction):
        return
    actor = get_current_actor()
    if not actor or not actor.is_authenticated:
        return

    tracked_fields = TRACKED_FIELDS.get(sender, ())
    previous_values = getattr(instance, "_audit_previous_values", None) or {}
    if created:
        changed_fields = list(tracked_fields)
    else:
        changed_fields = [
            field
            for field in tracked_fields
            if previous_values.get(field) != getattr(instance, field)
        ]

    action = _action_for(sender, instance, created)
    if not action:
        return
    AuditEvent.objects.using(using).create(
        actor=actor,
        action=action,
        content_type=ContentType.objects.db_manager(using).get_for_model(
            instance, for_concrete_model=False
        ),
        object_id=str(instance.pk),
        object_label=str(instance)[:255],
        details={"changed_fields": changed_fields},
    )