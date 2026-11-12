from django.contrib import admin
from .models import Resident

@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'room', 'joining_date')
    search_fields = ('full_name', 'phone', 'id_proof_number')