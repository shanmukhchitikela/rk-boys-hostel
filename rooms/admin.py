from django.contrib import admin

from .forms import RoomForm
from .models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    form = RoomForm
    list_display = ("room_number", "floor", "capacity", "monthly_fee", "updated_at")
    list_filter = ("floor",)
    search_fields = ("room_number", "notes")
    ordering = ("floor", "room_number")