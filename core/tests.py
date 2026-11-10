from io import StringIO
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import AnonymousUser, Group, User
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment
from residents.models import Resident, RoomAssignment
from rooms.models import Room

from .permissions import ROLE_GROUPS, role_required, user_has_role


class RolePermissionTests(TestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_user_has_assigned_role(self):
        user = User.objects.create_user(username="warden", password="test-password")
        user.groups.add(Group.objects.create(name="Warden"))

        self.assertTrue(user_has_role(user, "Warden"))
        self.assertFalse(user_has_role(user, "Owner"))

    def test_superuser_has_every_role(self):
        user = User.objects.create_superuser(
            username="owner", email="owner@example.com", password="test-password"
        )

        self.assertTrue(user_has_role(user, "Owner", "Manager", "Warden"))

    def test_role_required_redirects_anonymous_user_to_login(self):
        @role_required("Owner")
        def protected_view(request):
            return HttpResponse("ok")

        request = self.request_factory.get("/protected/")
        request.user = AnonymousUser()
        response = protected_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/?next=/protected/")

    def test_role_required_forbids_authenticated_user_without_role(self):
        @role_required("Owner")
        def protected_view(request):
            return HttpResponse("ok")

        request = self.request_factory.get("/protected/")
        request.user = User.objects.create_user(username="warden", password="test-password")

        self.assertEqual(protected_view(request).status_code, 403)

    def test_role_required_allows_user_with_role(self):
        @role_required("Owner")
        def protected_view(request):
            return HttpResponse("ok")

        user = User.objects.create_user(username="owner", password="test-password")
        user.groups.add(Group.objects.create(name="Owner"))
        request = self.request_factory.get("/protected/")
        request.user = user

        response = protected_view(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_group_creation_command_is_repeatable(self):
        call_command("create_role_groups", stdout=StringIO())
        call_command("create_role_groups", stdout=StringIO())

        self.assertEqual(
            set(Group.objects.values_list("name", flat=True)), set(ROLE_GROUPS)
        )


class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="manager", password="test-password")
        self.staff.groups.add(Group.objects.create(name="Manager"))
        self.today = timezone.localdate()
        self.period = BillingPeriod.objects.create(year=self.today.year, month=self.today.month)
        self.room = Room.objects.create(
            room_number="DASH-1", floor=0, capacity=4, monthly_fee=Decimal("250.00")
        )
        self.residents = [
            Resident.objects.create(
                full_name=f"Dashboard Resident {index}",
                phone=f"555-020{index}",
                joined_date=self.today - timedelta(days=30),
                agreed_monthly_fee=Decimal("100.00"),
            )
            for index in range(4)
        ]
        Resident.objects.create(
            full_name="Exited Resident",
            phone="555-0299",
            joined_date=self.today - timedelta(days=90),
            agreed_monthly_fee=Decimal("80.00"),
            status=Resident.Status.EXITED,
        )
        RoomAssignment.objects.create(
            resident=self.residents[0], room=self.room, start_date=self.today - timedelta(days=2)
        )

        due_dates = (
            self.today + timedelta(days=30),
            self.today - timedelta(days=1),
            self.today + timedelta(days=3),
            self.today + timedelta(days=8),
        )
        for resident, due_date in zip(self.residents, due_dates):
            charge = MonthlyCharge.objects.create(
                resident=resident,
                period=self.period,
                amount=resident.agreed_monthly_fee,
                due_date=due_date,
            )
            if due_date == due_dates[0]:
                Payment.objects.create(
                    charge=charge,
                    amount=charge.amount,
                    payment_mode=Payment.Mode.CASH,
                )
        AdvanceTransaction.objects.create(
            resident=self.residents[1],
            transaction_type=AdvanceTransaction.Type.DEPOSIT,
            amount=Decimal("999.00"),
            recorded_by=self.staff,
        )

    def test_dashboard_summarizes_database_for_selected_month(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("core:dashboard"),
            {"year": self.today.year, "month": self.today.month},
        )

        summary = response.context["summary"]
        self.assertEqual(summary["active_residents"], 4)
        self.assertEqual(summary["total_capacity"], 4)
        self.assertEqual(summary["vacancies"], 3)
        self.assertEqual(summary["expected_charges"], Decimal("400.00"))
        self.assertEqual(summary["amount_collected"], Decimal("100.00"))
        self.assertEqual(summary["remaining_balance"], Decimal("300.00"))
        self.assertEqual(summary["paid_count"], 1)
        self.assertEqual(summary["overdue_count"], 1)
        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["due_soon_count"], 1)