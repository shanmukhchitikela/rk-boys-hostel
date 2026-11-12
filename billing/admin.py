from django.contrib import admin
from .models import Charge, Payment

@admin.register(Charge)
class ChargeAdmin(admin.ModelAdmin):
    list_display = ('resident', 'title', 'amount', 'due_date', 'status', 'created_at')
    list_filter = ('status', 'due_date')
    search_fields = ('resident__full_name', 'title')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('charge', 'amount_paid', 'payment_date', 'payment_method')
    search_fields = ('charge__resident__full_name',)