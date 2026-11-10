from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment
from rooms.models import Room

from .admin import ResidentAdmin
from .forms import ResidentForm, RoomAssignmentForm
from .models import Resident, RoomAssignment


class ResidentModelAndFormTests(TestCase):
    def setUp(self):
        self.room = Room.objects.create(
            room_number="C-01", floor=1, capacity=1, monthly_fee=Decimal("450.00")
        )
        self.resident = Resident.objects.create(
            full_name="Avery Sample",
            phone="555-0101",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("450.00"),
        )

    def test_assignment_increments_room_occupancy(self):
        RoomAssignment.objects.create(
            resident=self.resident,
            room=self.room,
            start_date=date(2026, 1, 1),
        )

        self.room.refresh_from_db()
        self.assertEqual(self.room.active_occupants, 1)
        self.assertEqual(self.room.available_beds, 0)

    def test_full_room_rejects_another_active_assignment(self):
        RoomAssignment.objects.create(
            resident=self.resident,
            room=self.room,
            start_date=date(2026, 1, 1),
        )
        another_resident = Resident.objects.create(
            full_name="Jordan Example",
            phone="555-0102",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("450.00"),
        )
        form = RoomAssignmentForm(
            data={"room": self.room.pk, "start_date": "2026-02-01"},
            resident=another_resident,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("room", form.errors)

    def test_resident_cannot_have_two_active_assignments(self):
        second_room = Room.objects.create(
            room_number="C-02", floor=1, capacity=2, monthly_fee=Decimal("450.00")
        )
        RoomAssignment.objects.create(
            resident=self.resident,
            room=self.room,
            start_date=date(2026, 1, 1),
        )

        with self.assertRaisesMessage(
            ValidationError, "already has an active room assignment"
        ):
            RoomAssignment.objects.create(
                resident=self.resident,
                room=second_room,
                start_date=date(2026, 1, 2),
            )

    def test_exit_closes_assignment_and_preserves_history(self):
        assignment = RoomAssignment.objects.create(
            resident=self.resident,
            room=self.room,
            start_date=date(2026, 1, 1),
        )

        self.resident.mark_exited(date(2026, 2, 1))

        assignment.refresh_from_db()
        self.resident.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual(self.resident.status, Resident.Status.EXITED)
        self.assertEqual(assignment.end_date, date(2026, 2, 1))
        self.assertEqual(self.resident.room_assignments.count(), 1)
        self.assertEqual(self.room.available_beds, 1)

    def test_resident_admin_is_registered(self):
        self.assertIsInstance(admin.site._registry[Resident], ResidentAdmin)

    def test_resident_form_contains_requested_profile_fields(self):
        form = ResidentForm()

        self.assertEqual(
            set(form.fields),
            {
                "full_name",
                "phone",
                "emergency_contact",
                "id_proof_number",
                "room",
                "joining_date",
                "agreed_monthly_fee",
            },
        )

    def test_resident_form_assigns_room_and_creates_history(self):
        form = ResidentForm(
            data={
                "full_name": "Room Form Resident",
                "phone": "555-0140",
                "emergency_contact": "555-0141",
                "id_proof_number": "FORM-ID-140",
                "room": self.room.pk,
                "joining_date": "2026-02-01",
                "agreed_monthly_fee": "450.00",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        resident = form.save()

        self.room.refresh_from_db()
        self.assertEqual(resident.room_id, self.room.pk)
        self.assertEqual(self.room.active_occupants, 1)
        self.assertEqual(resident.room_assignments.count(), 1)

    def test_resident_form_rejects_full_room(self):
        occupant = Resident.objects.create(
            full_name="Existing Occupant",
            phone="555-0142",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("450.00"),
        )
        RoomAssignment.objects.create(
            resident=occupant,
            room=self.room,
            start_date=date(2026, 1, 1),
        )
        form = ResidentForm(
            data={
                "full_name": "Room Form Resident",
                "phone": "555-0140",
                "emergency_contact": "555-0141",
                "id_proof_number": "FORM-ID-141",
                "room": self.room.pk,
                "joining_date": "2026-02-01",
                "agreed_monthly_fee": "450.00",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("room", form.errors)


class ResidentViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="manager", password="test-password", is_staff=True
        )
        self.staff.groups.add(Group.objects.create(name="Manager"))
        self.resident = Resident.objects.create(
            full_name="Taylor Resident",
            phone="555-0110",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("500.00"),
        )

    def test_anonymous_resident_list_redirects_to_login(self):
        response = self.client.get(reverse("residents:list"))

        self.assertRedirects(response, "/accounts/login/?next=/residents/")

    def test_staff_can_search_and_filter_residents(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("residents:list"), {"q": "Taylor", "status": "active"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Taylor Resident")

    def test_staff_can_create_resident_profile(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("residents:create"),
            {
                "full_name": "Morgan New",
                "phone": "555-0111",
                "emergency_contact": "555-0112",
                "id_proof_number": "TEST-ID-1001",
                "joining_date": "2026-03-01",
                "agreed_monthly_fee": "525.00",
            },
        )

        self.assertRedirects(response, reverse("residents:detail", args=[2]))
        self.assertTrue(Resident.objects.filter(full_name="Morgan New").exists())

    def test_staff_can_assign_room_and_exit_resident(self):
        self.client.force_login(self.staff)
        room = Room.objects.create(
            room_number="D-01", floor=2, capacity=1, monthly_fee=Decimal("500.00")
        )

        assigned = self.client.post(
            reverse("residents:assign_room", args=[self.resident.pk]),
            {"room": room.pk, "start_date": "2026-01-02"},
        )
        self.assertRedirects(assigned, reverse("residents:detail", args=[self.resident.pk]))

        exited = self.client.post(reverse("residents:exit", args=[self.resident.pk]))
        self.assertRedirects(exited, reverse("residents:detail", args=[self.resident.pk]))
        self.assertEqual(RoomAssignment.objects.count(), 1)
        self.assertIsNotNone(RoomAssignment.objects.get().end_date)

    def test_staff_can_record_deposit_and_manager_can_apply_it(self):
        self.client.force_login(self.staff)
        today = timezone.localdate()
        period = BillingPeriod.objects.create(year=today.year, month=today.month)
        charge = MonthlyCharge.objects.create(
            resident=self.resident,
            period=period,
            amount=Decimal("500.00"),
            due_date=today + timezone.timedelta(days=10),
        )

        deposit_response = self.client.post(
            reverse("residents:advance_deposit", args=[self.resident.pk]),
            {"amount": "250.00", "date": today.isoformat(), "reference": "deposit-1", "notes": ""},
        )
        apply_response = self.client.post(
            reverse("residents:advance_apply", args=[self.resident.pk]),
            {
                "charge": charge.pk,
                "amount": "200.00",
                "date": today.isoformat(),
                "reference": "apply-1",
                "notes": "",
            },
        )

        self.assertRedirects(
            deposit_response, reverse("residents:detail", args=[self.resident.pk])
        )
        self.assertRedirects(
            apply_response, reverse("residents:detail", args=[self.resident.pk])
        )
        deposit = AdvanceTransaction.objects.get(transaction_type=AdvanceTransaction.Type.DEPOSIT)
        application = AdvanceTransaction.objects.get(
            transaction_type=AdvanceTransaction.Type.APPLY_TO_RENT
        )
        self.assertEqual(deposit.recorded_by, self.staff)
        self.assertEqual(application.recorded_by, self.staff)
        self.assertEqual(self.resident.advance_balance, Decimal("50.00"))
        self.assertEqual(Payment.objects.filter(payment_mode=Payment.Mode.ADVANCE).count(), 1)

    def test_manager_cannot_record_advance_refund(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("residents:advance_refund", args=[self.resident.pk])
        )

        self.assertEqual(response.status_code, 403)