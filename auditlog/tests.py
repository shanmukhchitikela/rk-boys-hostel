from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment
from residents.models import Resident
from rooms.models import Room

from .models import AuditEvent, HostelSettings


class AuditLogTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="audit-owner", password="test-password", is_staff=True
        )
        self.owner.groups.add(Group.objects.create(name="Owner"))
        self.manager = User.objects.create_user(username="audit-manager", password="test-password")
        self.manager.groups.add(Group.objects.create(name="Manager"))
        self.warden = User.objects.create_user(username="audit-warden", password="test-password")
        self.warden.groups.add(Group.objects.create(name="Warden"))
        today = timezone.localdate()
        self.resident = Resident.objects.create(
            full_name="Audit Resident",
            phone="555-0400",
            joined_date=today,
            agreed_monthly_fee=Decimal("350.00"),
        )
        self.room = Room.objects.create(
            room_number="AUD-1", floor=1, capacity=2, monthly_fee=Decimal("350.00")
        )
        self.period = BillingPeriod.objects.create(year=today.year, month=today.month)
        self.charge = MonthlyCharge.objects.create(
            resident=self.resident,
            period=self.period,
            amount=Decimal("350.00"),
            due_date=today,
        )

    def test_owner_can_update_database_settings_and_change_fields_are_audited(self):
        self.client.force_login(self.owner)
        settings_obj = HostelSettings.get_solo()

        response = self.client.post(
            reverse("auditlog:settings"),
            {
                "hostel_name": "Cedar House",
                "address": "8 Example Street",
                "phone_numbers": "555-0401\n555-0402",
                "email": "office@example.test",
                "receipt_text": "Thank you",
            },
        )

        self.assertRedirects(response, reverse("auditlog:settings"))
        settings_obj.refresh_from_db()
        event = AuditEvent.objects.get(action="hostel_settings_updated")
        self.assertEqual(settings_obj.hostel_name, "Cedar House")
        self.assertEqual(event.actor, self.owner)
        self.assertIn("receipt_text", event.details["changed_fields"])
        self.assertNotIn("Thank you", str(event.details))

    def test_resident_room_assignment_and_exit_are_audited(self):
        self.client.force_login(self.owner)
        today = timezone.localdate()

        resident_response = self.client.post(
            reverse("residents:create"),
            {
                "full_name": "New Audit Resident",
                "phone": "555-0403",
                "emergency_contact": "555-0405",
                "id_proof_number": "AUDIT-ID-1001",
                "joining_date": today.isoformat(),
                "agreed_monthly_fee": "300.00",
            },
        )
        resident = Resident.objects.get(full_name="New Audit Resident")
        room_response = self.client.post(
            reverse("rooms:create"),
            {
                "room_number": "AUD-2",
                "floor": 1,
                "capacity": 2,
                "monthly_fee": "300.00",
                "notes": "",
            },
        )
        room = Room.objects.get(room_number="AUD-2")
        resident_update_response = self.client.post(
            reverse("residents:edit", args=[resident.pk]),
            {
                "full_name": resident.full_name,
                "phone": "555-0404",
                "emergency_contact": "555-0405",
                "id_proof_number": "AUDIT-ID-1001",
                "joining_date": today.isoformat(),
                "agreed_monthly_fee": "300.00",
            },
        )
        room_update_response = self.client.post(
            reverse("rooms:edit", args=[room.pk]),
            {
                "room_number": room.room_number,
                "floor": room.floor,
                "capacity": 3,
                "monthly_fee": "300.00",
                "notes": "Updated room note",
            },
        )
        assignment_response = self.client.post(
            reverse("residents:assign_room", args=[resident.pk]),
            {"room": room.pk, "start_date": today.isoformat()},
        )
        exit_response = self.client.post(reverse("residents:exit", args=[resident.pk]))

        self.assertEqual(resident_response.status_code, 302)
        self.assertEqual(room_response.status_code, 302)
        self.assertEqual(resident_update_response.status_code, 302)
        self.assertEqual(room_update_response.status_code, 302)
        self.assertEqual(assignment_response.status_code, 302)
        self.assertEqual(exit_response.status_code, 302)
        self.assertTrue(
            AuditEvent.objects.filter(actor=self.owner, action="resident_created").exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(actor=self.owner, action="room_created").exists()
        )
        resident_update_event = AuditEvent.objects.get(
            actor=self.owner, action="resident_updated"
        )
        room_update_event = AuditEvent.objects.get(actor=self.owner, action="room_updated")
        self.assertIn("phone", resident_update_event.details["changed_fields"])
        self.assertIn("capacity", room_update_event.details["changed_fields"])
        self.assertNotIn("555-0404", str(resident_update_event.details))
        self.assertNotIn("Updated room note", str(room_update_event.details))
        self.assertTrue(
            AuditEvent.objects.filter(
                actor=self.owner, action="resident_assigned_to_room"
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(actor=self.owner, action="resident_exited").exists()
        )

    def test_payment_and_advance_actions_are_audited(self):
        self.client.force_login(self.owner)
        deposit_response = self.client.post(
            reverse("residents:advance_deposit", args=[self.resident.pk]),
            {
                "amount": "100.00",
                "date": timezone.localdate().isoformat(),
                "reference": "deposit-ref",
                "notes": "private note is not copied into audit details",
            },
        )
        payment_response = self.client.post(
            reverse("billing:payment_create", args=[self.charge.pk]),
            {
                "submission_key": "0f680e21-bf2e-42d2-bfbe-1715118d8a01",
                "amount": "25.00",
                "payment_mode": Payment.Mode.CASH,
                "reference": "cash-ref",
                "notes": "payment note",
            },
        )

        self.assertEqual(deposit_response.status_code, 302)
        self.assertEqual(payment_response.status_code, 302)
        self.assertTrue(
            AuditEvent.objects.filter(actor=self.owner, action="advance_deposit_recorded").exists()
        )
        payment_event = AuditEvent.objects.get(action="payment_recorded")
        self.assertEqual(payment_event.actor, self.owner)
        self.assertNotIn("payment note", str(payment_event.details))

    def test_audit_history_is_limited_to_owner_and_manager(self):
        self.client.force_login(self.manager)
        manager_response = self.client.get(reverse("auditlog:history"))
        self.assertEqual(manager_response.status_code, 200)

        self.client.force_login(self.warden)
        warden_response = self.client.get(reverse("auditlog:history"))
        settings_response = self.client.get(reverse("auditlog:settings"))

        self.assertEqual(warden_response.status_code, 403)
        self.assertEqual(settings_response.status_code, 403)