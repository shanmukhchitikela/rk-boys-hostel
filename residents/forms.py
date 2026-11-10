from django import forms
from .models import Resident, RoomAssignment

class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = ['full_name', 'phone', 'emergency_contact', 'id_proof_number', 'room', 'agreed_monthly_fee', 'joining_date', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'id_proof_number': forms.TextInput(attrs={'class': 'form-control'}),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'agreed_monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Optional custom rent'}),
            'joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        is_active = cleaned_data.get('is_active', True)

        if room and is_active:
            current_resident_pk = self.instance.pk
            assigned_count = room.residents.filter(is_active=True).exclude(pk=current_resident_pk).count()
            if assigned_count >= room.capacity:
                raise forms.ValidationError(f"Room {room.room_number} is already at full capacity ({room.capacity} beds).")

        return cleaned_data

class RoomAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoomAssignment
        fields = ['resident', 'room', 'start_date', 'end_date']
        widgets = {
            'resident': forms.Select(attrs={'class': 'form-control'}),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }