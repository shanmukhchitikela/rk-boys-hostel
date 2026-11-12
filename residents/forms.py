from django import forms
from .models import Resident
from rooms.models import Room

class ResidentForm(forms.ModelForm):
    class Meta:
        model = Resident
        fields = [
            'full_name', 
            'phone', 
            'id_proof_number', 
            'id_proof_image', 
            'email', 
            'emergency_contact', 
            'room', 
            'joining_date'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'id_proof_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ID Proof / Aadhaar Number'}),
            'id_proof_image': forms.FileInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address (optional)'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emergency Contact Number'}),
            'room': forms.Select(attrs={'class': 'form-control'}),
            'joining_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')

        if room:
            current_resident_pk = self.instance.pk
            assigned_count = room.residents.exclude(pk=current_resident_pk).count()
            if assigned_count >= room.capacity:
                raise forms.ValidationError(f"Room {room.room_number} is already at full capacity ({room.capacity} beds).")

        return cleaned_data
