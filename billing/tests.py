from datetime import date, timedelta
from decimal import Decimal
import uuid

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from residents.models import Resident
from rooms.models import Room
from auditlog.models import HostelSettings

from .admin import PaymentAdmin
from .models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment


class BillingModelTests(TestCase):
    def setUp(self):
        self.resident = Resident.objects.create(
            full_name="Billing Resident",
            phone="555-0199",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("300.00"),
        )
        self.period = BillingPeriod.objects.create(year=2026, month=1)
        self.charge = MonthlyCharge.objects.create(
            resident=self.resident,
            period=self.period,
            amount=Decimal("300.00"),
            due_date=timezone.localdate() + timedelta(days=14),
        )

    def test_partial_payments_are_summed_and_status_is_derived(self):
        Payment.objects.create(
            charge=self.charge,
            amount=Decimal("100.00"),
            payment_mode=Payment.Mode.CASH,
        )
        Payment.objects.create(
            charge=self.charge,
            amount=Decimal("75.00"),
            payment_mode=Payment.Mode.BANK_TRANSFER,
        )

        self.assertEqual(self.charge.paid_amount, Decimal("175.00"))
        self.assertEqual(self.charge.pending_amount, Decimal("125.00"))
        self.assertEqual(self.charge.status, MonthlyCharge.Status.PENDING)

    def test_charge_status_uses_configured_local_date(self):
        self.charge.due_date = timezone.localdate() - timedelta(days=1)
        self.assertEqual(self.charge.status, MonthlyCharge.Status.OVERDUE)
        self.charge.due_date = timezone.localdate() + timedelta(days=7)
        self.assertEqual(self.charge.status, MonthlyCharge.Status.DUE_SOON)
        self.charge.due_date = timezone.localdate() + timedelta(days=8)
        self.assertEqual(self.charge.status, MonthlyCharge.Status.PENDING)

    def test_paid_status_and_receipt_are_calculated_and_generated(self):
        payment = Payment.objects.create(
            charge=self.charge,
            amount=Decimal("300.00"),
            payment_mode=Payment.Mode.CHEQUE,
        )

        self.assertTrue(payment.receipt_number.startswith("RCT-"))
        self.assertEqual(self.charge.status, MonthlyCharge.Status.PAID)
        self.assertEqual(self.charge.pending_amount, Decimal("0.00"))

    def test_payment_cannot_exceed_outstanding_balance(self):
        Payment.objects.create(
            charge=self.charge,
            amount=Decimal("250.00"),
            payment_mode=Payment.Mode.CASH,
        )

        with self.assertRaisesMessage(
            ValidationError, "Payment cannot exceed the remaining charge balance"
        ):
            Payment.objects.create(
                charge=self.charge,
                amount=Decimal("51.00"),
                payment_mode=Payment.Mode.CASH,
            )

    def test_same_resident_cannot_have_duplicate_period_charge(self):
        duplicate = MonthlyCharge(
            resident=self.resident,
            period=self.period,
            amount=Decimal("300.00"),
            due_date=self.charge.due_date,
        )

        with self.assertRaises(ValidationError):
            duplicate.save()

    def test_payment_is_registered_in_admin(self):
        self.assertIsInstance(admin.site._registry[Payment], PaymentAdmin)


class BillingViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="owner", password="test-password")
        self.staff.groups.add(Group.objects.create(name="Owner"))
        self.resident = Resident.objects.create(
            full_name="Morgan Billing",
            phone="555-0120",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("325.00"),
        )
        self.period = BillingPeriod.objects.create(year=2026, month=1)
        self.charge = MonthlyCharge.objects.create(
            resident=self.resident,
            period=self.period,
            amount=self.resident.agreed_monthly_fee,
            due_date=timezone.localdate() + timedelta(days=10),
        )

    def test_anonymous_user_is_redirected(self):
        response = self.client.get(reverse("billing:charge_list"))

        self.assertRedirects(response, "/accounts/login/?next=/billing/")

    def test_staff_can_filter_charges_by_period_and_status(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("billing:charge_list"),
            {"year": "2026", "month": "1", "status": "pending"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Morgan Billing")

    def test_staff_can_open_charge_and_payment_forms(self):
        self.client.force_login(self.staff)

        charge_response = self.client.get(reverse("billing:charge_create"))
        payment_response = self.client.get(
            reverse("billing:payment_create", args=[self.charge.pk])
        )

        self.assertTemplateUsed(charge_response, "billing/charge_form.html")
        self.assertTemplateUsed(payment_response, "billing/payment_form.html")

    def test_staff_can_create_charge_from_current_agreed_fee(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("billing:charge_create"),
            {
                "resident": self.resident.pk,
                "year": 2026,
                "month": 2,
                "due_date": (timezone.localdate() + timedelta(days=12)).isoformat(),
            },
        )

        charge = MonthlyCharge.objects.get(period__year=2026, period__month=2)
        self.assertRedirects(response, reverse("billing:charge_detail", args=[charge.pk]))
        self.assertEqual(charge.amount, self.resident.agreed_monthly_fee)

    def test_duplicate_payment_post_creates_only_one_payment(self):
        self.client.force_login(self.staff)
        submission_key = uuid.uuid4()
        data = {
            "submission_key": str(submission_key),
            "amount": "240.00",
            "payment_mode": Payment.Mode.CASH,
            "reference": "",
            "notes": "",
        }

        first_response = self.client.post(
            reverse("billing:payment_create", args=[self.charge.pk]), data
        )
        second_response = self.client.post(
            reverse("billing:payment_create", args=[self.charge.pk]), data
        )

        self.assertEqual(Payment.objects.filter(idempotency_key=submission_key).count(), 1)
        self.assertRedirects(
            first_response, reverse("billing:charge_detail", args=[self.charge.pk])
        )
        self.assertRedirects(
            second_response, reverse("billing:charge_detail", args=[self.charge.pk])
        )

    def test_charge_detail_shows_receipt_history(self):
        self.client.force_login(self.staff)
        payment = Payment.objects.create(
            charge=self.charge,
            amount=Decimal("50.00"),
            payment_mode=Payment.Mode.OTHER,
            reference="counter-1",
        )

        response = self.client.get(reverse("billing:charge_detail", args=[self.charge.pk]))

        self.assertContains(response, payment.receipt_number)
        self.assertContains(response, "counter-1")

    def test_receipt_uses_saved_payment_and_room_for_billing_period(self):
        self.client.force_login(self.staff)
        hostel_settings = HostelSettings.get_solo()
        hostel_settings.hostel_name = "North House"
        hostel_settings.address = "12 Example Lane"
        hostel_settings.phone_numbers = "555-0100"
        hostel_settings.save()
        from residents.models import RoomAssignment

        room = Room.objects.create(
            room_number="REC-1", floor=0, capacity=2, monthly_fee=Decimal("325.00")
        )
        RoomAssignment.objects.create(
            resident=self.resident,
            room=room,
            start_date=date(2026, 1, 1),
        )
        payment = Payment.objects.create(
            charge=self.charge,
            amount=Decimal("75.00"),
            payment_mode=Payment.Mode.BANK_TRANSFER,
            reference="bank-ref-1",
        )

        response = self.client.get(reverse("billing:payment_receipt", args=[payment.pk]))

        self.assertTemplateUsed(response, "billing/payment_receipt.html")
        self.assertContains(response, "North House")
        self.assertContains(response, "12 Example Lane")
        self.assertContains(response, "REC-1")
        self.assertContains(response, payment.receipt_number)
        self.assertContains(response, "Bank transfer")

    def test_payment_records_cannot_be_edited(self):
        payment = Payment.objects.create(
            charge=self.charge,
            amount=Decimal("25.00"),
            payment_mode=Payment.Mode.CASH,
        )
        payment.amount = Decimal("20.00")

        with self.assertRaisesMessage(ValidationError, "Recorded payments are immutable"):
            payment.save()

    def test_warden_cannot_open_advance_apply_or_refund(self):
        from residents.models import Resident

        warden = User.objects.create_user(username="warden", password="test-password")
        warden.groups.add(Group.objects.create(name="Warden"))
        self.client.force_login(warden)

        apply_response = self.client.get(
            reverse("residents:advance_apply", args=[self.resident.pk])
        )
        refund_response = self.client.get(
            reverse("residents:advance_refund", args=[self.resident.pk])
        )

        self.assertEqual(apply_response.status_code, 403)
        self.assertEqual(refund_response.status_code, 403)

    def test_paid_resident_roster_uses_selected_month_and_search(self):
        self.client.force_login(self.staff)
        Payment.objects.create(
            charge=self.charge,
            amount=self.charge.amount,
            payment_mode=Payment.Mode.CASH,
        )

        response = self.client.get(
            reverse("billing:paid_residents"),
            {"year": 2026, "month": 1, "q": "Morgan"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Morgan Billing")
        self.assertTemplateUsed(response, "billing/paid_residents.html")

    def test_attention_roster_filters_due_soon_and_overdue(self):
        self.client.force_login(self.staff)
        self.charge.due_date = timezone.localdate() - timedelta(days=1)
        self.charge.save()
        due_soon_resident = Resident.objects.create(
            full_name="Soon Resident",
            phone="555-0121",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("225.00"),
        )
        due_soon_charge = MonthlyCharge.objects.create(
            resident=due_soon_resident,
            period=self.period,
            amount=Decimal("225.00"),
            due_date=timezone.localdate() + timedelta(days=3),
        )

        overdue_response = self.client.get(
            reverse("billing:attention_residents"),
            {"year": 2026, "month": 1, "status": MonthlyCharge.Status.OVERDUE},
        )
        due_soon_response = self.client.get(
            reverse("billing:attention_residents"),
            {"year": 2026, "month": 1, "status": MonthlyCharge.Status.DUE_SOON},
        )

        self.assertContains(overdue_response, "Morgan Billing")
        self.assertNotContains(overdue_response, "Soon Resident")
        self.assertContains(due_soon_response, "Soon Resident")
        self.assertNotContains(due_soon_response, "Morgan Billing")
        self.assertEqual(due_soon_charge.status, MonthlyCharge.Status.DUE_SOON)


class AdvanceLedgerTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="finance", password="test-password")
        self.resident = Resident.objects.create(
            full_name="Advance Resident",
            phone="555-0130",
            joined_date=date(2026, 1, 1),
            agreed_monthly_fee=Decimal("300.00"),
        )
        self.period = BillingPeriod.objects.create(year=2026, month=2)
        self.charge = MonthlyCharge.objects.create(
            resident=self.resident,
            period=self.period,
            amount=Decimal("300.00"),
            due_date=timezone.localdate() + timedelta(days=14),
        )

    def make_transaction(self, transaction_type, amount, **kwargs):
        return AdvanceTransaction.objects.create(
            resident=self.resident,
            transaction_type=transaction_type,
            amount=Decimal(amount),
            recorded_by=self.staff,
            **kwargs,
        )

    def test_advance_balance_is_derived_from_ledger(self):
        self.make_transaction(AdvanceTransaction.Type.DEPOSIT, "200.00")
        self.make_transaction(AdvanceTransaction.Type.REFUND, "25.00")

        self.assertEqual(self.resident.advance_balance, Decimal("175.00"))
        self.assertEqual(Payment.objects.count(), 0)

    def test_apply_to_rent_creates_linked_payment_and_reduces_balance(self):
        self.make_transaction(AdvanceTransaction.Type.DEPOSIT, "200.00")

        transaction = self.make_transaction(
            AdvanceTransaction.Type.APPLY_TO_RENT,
            "200.00",
            charge=self.charge,
            reference="advance-apply",
        )

        self.assertEqual(self.resident.advance_balance, Decimal("0.00"))
        self.assertEqual(transaction.payment.amount, Decimal("200.00"))
        self.assertEqual(transaction.payment.payment_mode, Payment.Mode.ADVANCE)
        self.assertEqual(self.charge.pending_amount, Decimal("100.00"))
        self.assertEqual(transaction.recorded_by, self.staff)

    def test_apply_and_refund_cannot_exceed_available_balance(self):
        self.make_transaction(AdvanceTransaction.Type.DEPOSIT, "50.00")

        with self.assertRaisesMessage(ValidationError, "available advance balance"):
            self.make_transaction(
                AdvanceTransaction.Type.APPLY_TO_RENT,
                "51.00",
                charge=self.charge,
            )
        with self.assertRaisesMessage(ValidationError, "available advance balance"):
            self.make_transaction(AdvanceTransaction.Type.REFUND, "51.00")

        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(AdvanceTransaction.objects.count(), 1)

    def test_advance_entries_are_immutable(self):
        entry = self.make_transaction(AdvanceTransaction.Type.DEPOSIT, "50.00")
        entry.amount = Decimal("40.00")

        with self.assertRaisesMessage(ValidationError, "Advance ledger entries are immutable"):
            entry.save()
