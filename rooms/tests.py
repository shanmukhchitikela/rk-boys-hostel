from decimal import Decimal
from unittest.mock import PropertyMock, patch

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .admin import RoomAdmin
from .forms import RoomForm
from .models import Room


class RoomModelAndFormTests(TestCase):
    def test_available_beds_equal_capacity_before_assignments_exist(self):
        room = Room.objects.create(
            room_number="A-01", floor=0, capacity=4, monthly_fee=Decimal("425.00")
        )

        self.assertEqual(room.active_occupants, 0)
        self.assertEqual(room.available_beds, 4)

    def test_capacity_cannot_be_reduced_below_active_occupants(self):
        room = Room.objects.create(
            room_number="A-02", floor=0, capacity=4, monthly_fee=Decimal("425.00")
        )
        form_data = {
            "room_number": room.room_number,
            "floor": room.floor,
            "capacity": 2,
            "monthly_fee": "425.00",
            "notes": "",
        }

        with patch.object(Room, "active_occupants", new_callable=PropertyMock, return_value=3):
            form = RoomForm(data=form_data, instance=room)
            is_valid = form.is_valid()

        self.assertFalse(is_valid)
        self.assertIn("Capacity cannot be lower", str(form.errors["capacity"]))

    def test_room_number_must_be_unique(self):
        Room.objects.create(
            room_number="A-03", floor=0, capacity=2, monthly_fee=Decimal("300.00")
        )
        form = RoomForm(
            data={
                "room_number": "A-03",
                "floor": 0,
                "capacity": 2,
                "monthly_fee": "300.00",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("room_number", form.errors)

    def test_room_is_registered_in_admin(self):
        self.assertIsInstance(admin.site._registry[Room], RoomAdmin)


class RoomViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="warden", password="test-password")
        self.user.groups.add(Group.objects.create(name="Warden"))

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse("rooms:list"))

        self.assertRedirects(response, "/accounts/login/?next=/rooms/")

    def test_signed_in_user_without_staff_role_is_forbidden(self):
        user = User.objects.create_user(username="resident", password="test-password")
        self.client.force_login(user)

        self.assertEqual(self.client.get(reverse("rooms:list")).status_code, 403)

    def test_staff_user_can_view_room_list(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("rooms:list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rooms/room_list.html")

    def test_staff_user_can_create_room(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("rooms:create"),
            {
                "room_number": "B-10",
                "floor": 1,
                "capacity": 3,
                "monthly_fee": "500.00",
                "notes": "Corner room",
            },
        )

        self.assertRedirects(response, reverse("rooms:list"))
        self.assertTrue(Room.objects.filter(room_number="B-10").exists())