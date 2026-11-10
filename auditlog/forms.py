from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from core.permissions import ROLE_GROUPS
from .models import AuditEvent, HostelSettings


class HostelSettingsForm(forms.ModelForm):
    class Meta:
        model = HostelSettings
        fields = ("hostel_name", "address", "phone_numbers", "email", "receipt_text")
        labels = {
            "hostel_name": "Hostel name",
            "phone_numbers": "Phone numbers",
            "receipt_text": "Receipt text",
        }
        widgets = {
            "hostel_name": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "phone_numbers": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "receipt_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }


class AuditFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Search",
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Record or staff user"}),
    )
    action = forms.ChoiceField(
        required=False,
        choices=(('', "All actions"),),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    actor = forms.ModelChoiceField(
        required=False,
        queryset=get_user_model()
        .objects.filter(Q(groups__name__in=ROLE_GROUPS) | Q(is_superuser=True))
        .distinct()
        .order_by("username"),
        empty_label="All staff",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    date_from = forms.DateField(
        required=False,
        label="From",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        label="To",
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        actions = AuditEvent.objects.order_by().values_list("action", flat=True).distinct()
        self.fields["action"].choices = (('', "All actions"),) + tuple(
            (action, action.replace("_", " ").title()) for action in actions
        )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")
        if date_from and date_to and date_from > date_to:
            self.add_error("date_to", "End date must be on or after start date.")
        return cleaned_data