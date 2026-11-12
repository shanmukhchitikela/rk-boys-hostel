from django.db import models

class Resident(models.Model):
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    id_proof_number = models.CharField(max_length=50, unique=True)
    id_proof_image = models.ImageField(upload_to='id_proofs/', blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    joining_date = models.DateField()
    emergency_contact = models.CharField(max_length=15, blank=True, null=True)
    room = models.ForeignKey('rooms.Room', on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')

    def __str__(self):
        room_label = f"Room {self.room.room_number}" if self.room else "Unassigned"
        return f"{self.full_name} ({room_label})"

    @property
    def is_active(self):
        return True
