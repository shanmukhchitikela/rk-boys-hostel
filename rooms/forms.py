from django import forms
from django.core.exceptions import ValidationError
from .models import Room

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ("room_number", "floor", "capacity", "monthly_fee", "notes")
        labels = {"monthly_fee": "Monthly fee per bed"}
        widgets = {
            "room_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. 101"}),
            "floor": forms.NumberInput(attrs={"class": "form-control", "min": 0, "placeholder": "Floor number"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "Bed capacity"}),
            "monthly_fee": forms.NumberInput(attrs={"class": "form-control", "min": 0, "step": "0.01", "placeholder": "Rent in ₹"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Optional notes"}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")
        if capacity is not None and self.instance.pk and capacity < self.instance.active_occupants:
            raise ValidationError(
                f"Capacity cannot be lower than current occupants ({self.instance.active_occupants} beds occupied)."
            )
        return capacity
