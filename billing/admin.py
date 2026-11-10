from django.contrib import admin

from .models import AdvanceTransaction, BillingPeriod, MonthlyCharge, Payment


@admin.register(BillingPeriod)
class BillingPeriodAdmin(admin.ModelAdmin):
    list_display = ("year", "month")
    ordering = ("-year", "-month")


@admin.register(MonthlyCharge)
class MonthlyChargeAdmin(admin.ModelAdmin):
    list_display = ("resident", "period", "amount", "due_date", "status_label")
    list_filter = ("period__year", "period__month", "due_date")
    search_fields = ("resident__full_name", "resident__phone")
    autocomplete_fields = ("resident",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "charge", "amount", "payment_mode", "recorded_at")
    list_filter = ("payment_mode", "recorded_at")
    search_fields = ("receipt_number", "reference", "charge__resident__full_name")
    readonly_fields = tuple(field.name for field in Payment._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AdvanceTransaction)
class AdvanceTransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "resident", "transaction_type", "amount", "recorded_by", "charge")
    list_filter = ("transaction_type", "date")
    search_fields = ("resident__full_name", "resident__phone", "reference")
    readonly_fields = tuple(field.name for field in AdvanceTransaction._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False