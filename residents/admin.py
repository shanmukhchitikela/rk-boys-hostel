from django.contrib import admin, messages

from .models import Resident, RoomAssignment


@admin.register(Resident)
class ResidentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone",
        "room",
        "joining_date",
        "is_active",
        "agreed_monthly_fee",
    )
    list_filter = ("is_active", "room", "joining_date")
    search_fields = ("full_name", "phone", "emergency_contact")
    readonly_fields = ("room", "is_active", "created_at", "updated_at")
    actions = ("mark_selected_as_exited",)

    @admin.action(description="Mark selected residents as exited")
    def mark_selected_as_exited(self, request, queryset):
        for resident in queryset:
            resident.mark_exited()
        self.message_user(request, "Selected residents marked as exited.", messages.SUCCESS)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RoomAssignment)
class RoomAssignmentAdmin(admin.ModelAdmin):
    list_display = ("resident", "room", "start_date", "end_date")
    list_filter = ("room", "start_date", "end_date")
    search_fields = ("resident__full_name", "resident__phone", "room__room_number")
    autocomplete_fields = ("resident", "room")

    def has_delete_permission(self, request, obj=None):
        return False