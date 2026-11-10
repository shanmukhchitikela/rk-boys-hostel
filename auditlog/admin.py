from django.contrib import admin

from core.permissions import user_has_role

from .models import AuditEvent, HostelSettings


@admin.register(HostelSettings)
class HostelSettingsAdmin(admin.ModelAdmin):
    fields = ("hostel_name", "address", "phone_numbers", "email", "receipt_text", "updated_at")
    readonly_fields = ("updated_at",)

    def has_module_permission(self, request):
        return user_has_role(request.user, "Owner")

    def has_view_permission(self, request, obj=None):
        return user_has_role(request.user, "Owner")

    def has_add_permission(self, request):
        return user_has_role(request.user, "Owner") and not HostelSettings.objects.exists()

    def has_change_permission(self, request, obj=None):
        return user_has_role(request.user, "Owner")

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        obj.singleton_key = "main"
        super().save_model(request, obj, form, change)


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "actor", "action", "content_type", "object_id", "object_label")
    list_filter = ("action", "content_type", "timestamp")
    search_fields = ("actor__username", "action", "object_label", "object_id")
    readonly_fields = tuple(field.name for field in AuditEvent._meta.fields)

    def has_module_permission(self, request):
        return user_has_role(request.user, "Owner", "Manager")

    def has_view_permission(self, request, obj=None):
        return user_has_role(request.user, "Owner", "Manager")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False