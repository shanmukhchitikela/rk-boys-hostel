from django.db import models
from django.db import transaction
from rooms.models import Room

class Resident(models.Model):
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    emergency_contact = models.CharField(max_length=15)
    id_proof_number = models.CharField(
        max_length=50, 
        unique=True, 
        help_text="Aadhaar or Govt ID"
    )
    room = models.ForeignKey(
        Room, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="residents"
    )
    agreed_monthly_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Custom agreed fee per month"
    )
    joining_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        room_num = self.room.room_number if self.room else 'No Room'
        return f"{self.full_name} ({room_num})"

class RoomAssignment(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="assignments")
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="assignments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            Resident.objects.select_for_update().get(pk=self.resident_id)
            Room.objects.select_for_update().get(pk=self.room_id)
            result = super().save(*args, **kwargs)
            if self.end_date is None:
                Resident.objects.filter(pk=self.resident_id).update(room_id=self.room_id)
            else:
                Resident.objects.filter(
                    pk=self.resident_id, room_id=self.room_id
                ).update(room_id=None)
            return result