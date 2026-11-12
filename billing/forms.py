from django import forms
from .models import Charge, Payment

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

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['charge', 'amount_paid', 'payment_method']
        widgets = {
            'charge': forms.Select(attrs={'class': 'form-control'}),
            'amount_paid': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'payment_method': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UPI, Cash, Bank Transfer'}),
        }
