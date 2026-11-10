import csv
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment
from residents.models import Resident, RoomAssignment
from rooms.models import Room


class ReportsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="report-owner", password="test-password")
        self.owner.groups.add(Group.objects.create(name="Owner"))
        self.warden = User.objects.create_user(username="report-warden", password="test-password")
        self.warden.groups.add(Group.objects.create(name="Warden"))
        today = timezone.localdate()
        self.period = BillingPeriod.objects.create(year=today.year, month=today.month)
        self.resident = Resident.objects.create(
            full_name="=Resident Report",
            phone="+555-0190",
            joined_date=today,
            agreed_monthly_fee=Decimal("120.00"),
        )
        self.room = Room.objects.create(
            room_number="=R-1", floor=1, capacity=2, monthly_fee=Decimal("120.00")
        )
        RoomAssignment.objects.create(
            resident=self.resident,
            room=self.room,
            start_date=today,
        )
        self.charge = MonthlyCharge.objects.create(
            resident=self.resident,
            period=self.period,
            amount=Decimal("120.00"),
            due_date=today + timedelta(days=14),
        )
        self.payment = Payment.objects.create(
            charge=self.charge,
            amount=Decimal("40.00"),
            payment_mode=Payment.Mode.BANK_TRANSFER,
            reference="=REF-1",
        )
        self.advance = AdvanceTransaction.objects.create(
            resident=self.resident,
            transaction_type=AdvanceTransaction.Type.DEPOSIT,
            amount=Decimal("75.00"),
            date=today,
            reference="+ADV-1",
            recorded_by=self.owner,
        )
        self.month_params = {"year": today.year, "month": today.month}

    def get_csv_rows(self, route_name, extra_params=None):
        self.client.force_login(self.owner)
        params = {**self.month_params, **(extra_params or {})}
        response = self.client.get(reverse(route_name), params)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        return list(csv.reader(StringIO(response.content.decode("utf-8"))))

    def test_reports_page_shows_filtered_totals(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("reports:index"), self.month_params)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["resident_count"], 1)
        self.assertEqual(response.context["total_capacity"], 2)
        self.assertEqual(response.context["occupied_beds"], 1)
        self.assertEqual(response.context["vacancies"], 1)
        self.assertEqual(response.context["expected_charges"], Decimal("120.00"))
        self.assertEqual(response.context["amount_collected"], Decimal("40.00"))
        self.assertEqual(response.context["remaining_balance"], Decimal("80.00"))
        self.assertEqual(response.context["deposit_total"], Decimal("75.00"))

    def test_resident_export_is_minimal_and_formula_safe(self):
        rows = self.get_csv_rows("reports:residents_csv")

        self.assertEqual(
            rows[0], ["Full name", "Phone", "Joined date", "Status", "Current room"]
        )
        self.assertEqual(rows[1][0], "'=Resident Report")
        self.assertEqual(rows[1][1], "'+555-0190")
        self.assertNotIn("password", ",".join(rows[0]).lower())
        self.assertNotIn("document", ",".join(rows[0]).lower())

    def test_room_export_includes_current_occupancy_and_vacancy(self):
        rows = self.get_csv_rows("reports:rooms_csv")

        self.assertEqual(rows[0], ["Room number", "Floor", "Capacity", "Active occupants", "Available beds"])
        self.assertEqual(rows[1], ["'=R-1", "1", "2", "1", "1"])

    def test_monthly_charge_and_payment_exports_use_selected_month(self):
        charges = self.get_csv_rows("reports:charges_csv")
        payments = self.get_csv_rows("reports:payments_csv")

        self.assertEqual(charges[1][0], str(self.period))
        self.assertEqual(charges[1][1], "'=Resident Report")
        self.assertEqual(charges[1][2:5], ["120.00", "40.00", "80.00"])
        self.assertEqual(payments[1][2], self.payment.receipt_number)
        self.assertEqual(payments[1][5], "40.00")
        self.assertEqual(payments[1][6], "'=REF-1")

    def test_advance_export_includes_type_reference_and_recorder(self):
        rows = self.get_csv_rows("reports:advances_csv")

        self.assertEqual(rows[1][1], "'=Resident Report")
        self.assertEqual(rows[1][2], "Deposit")
        self.assertEqual(rows[1][3], "75.00")
        self.assertEqual(rows[1][4], "'+ADV-1")
        self.assertEqual(rows[1][6], self.owner.get_username())

    def test_warden_can_export_operations_but_not_financial_data(self):
        self.client.force_login(self.warden)

        residents_response = self.client.get(
            reverse("reports:residents_csv"), self.month_params
        )
        rooms_response = self.client.get(reverse("reports:rooms_csv"), self.month_params)
        charges_response = self.client.get(
            reverse("reports:charges_csv"), self.month_params
        )
        advances_response = self.client.get(
            reverse("reports:advances_csv"), self.month_params
        )

        self.assertEqual(residents_response.status_code, 200)
        self.assertEqual(rooms_response.status_code, 200)
        self.assertEqual(charges_response.status_code, 403)
        self.assertEqual(advances_response.status_code, 403)

    def test_anonymous_user_is_redirected_from_reports(self):
        response = self.client.get(reverse("reports:index"))

        self.assertRedirects(response, "/accounts/login/?next=/reports/")