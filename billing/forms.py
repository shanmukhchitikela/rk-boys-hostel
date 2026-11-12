from django import forms
from .models import Charge, Payment
from residents.models import Resident
from rooms.utils import natural_resident_key

class ChargeForm(forms.ModelForm):
    class Meta:
        model = Charge
        fields = ['resident', 'title', 'amount', 'due_date', 'status']
        widgets = {
            'resident': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Monthly Rent - Nov 2026'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sorted_residents = sorted(Resident.objects.select_related('room').all(), key=natural_resident_key)
        self.fields['resident'].choices = [('', '---------')] + [
            (r.id, f"{f'Room {r.room.room_number}' if r.room else 'Unassigned'} — {r.full_name} ({r.phone})")
            for r in sorted_residents
        ]

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount_paid', 'payment_date', 'payment_method', 'reference', 'notes']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. UPI Ref / Cheque No / Cash receipt'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional remarks'}),
        }
