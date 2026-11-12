from django.db import models
from django.core.validators import MinValueValidator
from .utils import natural_room_key

class Room(models.Model):
    room_number = models.CharField(max_length=20, unique=True, help_text="Unique room number")
    floor = models.IntegerField(help_text="Floor number")
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Total bed capacity"
    )
    monthly_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Monthly fee per bed"
    )
    notes = models.TextField(blank=True, null=True, help_text="Optional room notes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Room {self.room_number} (Floor {self.floor})"

    @property
    def fee(self):
        return self.monthly_fee

    @property
    def natural_sort_key(self):
        return natural_room_key(self)

    @property
    def active_occupants(self):
        if hasattr(self, 'residents'):
            return self.residents.count()
        return self.resident_set.count()

    @property
    def available_beds(self):
        return max(0, self.capacity - self.active_occupants)
