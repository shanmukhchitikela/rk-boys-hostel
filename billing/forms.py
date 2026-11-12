from django import forms
from .models import Charge, Payment

class ChargeForm(forms.ModelForm):
    class Meta:
        model = Charge
        fields = ['resident', 'title', 'amount', 'due_date', 'status']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['charge', 'amount_paid', 'payment_method']