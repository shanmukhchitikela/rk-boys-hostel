from django import forms
from django.core.exceptions import ValidationError

from .models import Room


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ("room_number", "floor", "capacity", "monthly_fee", "notes")
        labels = {"monthly_fee": "Listed monthly fee"}
        widgets = {
            "room_number": forms.TextInput(attrs={"class": "form-control"}),
            "floor": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "monthly_fee": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": "0.01"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if self.instance.pk and capacity < self.instance.active_occupants:
            raise ValidationError(
                "Capacity cannot be lower than the number of active occupants."
            )
        return capacity