from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from core.permissions import role_required

from .forms import RoomForm
from .models import Room


@role_required("Owner", "Manager", "Warden")
def room_list(request):
    rooms = list(
        Room.objects.annotate(
            annotated_active_occupants=Count(
                "assignments", filter=Q(assignments__end_date__isnull=True)
            )
        )
    )
    context = {
        "rooms": rooms,
        "room_count": len(rooms),
        "total_capacity": sum(room.capacity for room in rooms),
        "active_occupants": sum(room.active_occupants for room in rooms),
        "available_beds": sum(room.available_beds for room in rooms),
    }
    return render(request, "rooms/room_list.html", context)


@role_required("Owner", "Manager", "Warden")
def room_create(request):
    form = RoomForm(data=request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room created.")
        return redirect("rooms:list")
    return render(request, "rooms/room_form.html", {"form": form, "is_edit": False})


@role_required("Owner", "Manager", "Warden")
def room_update(request, pk):
    room = get_object_or_404(Room, pk=pk)
    form = RoomForm(
        data=request.POST if request.method == "POST" else None,
        instance=room,
    )
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for field, errors in error.message_dict.items():
                    target = field if field in form.fields else None
                    for message in errors:
                        form.add_error(target, message)
            else:
                form.add_error(None, error)
        else:
            messages.success(request, "Room updated.")
            return redirect("rooms:list")
    return render(
        request,
        "rooms/room_form.html",
        {"form": form, "is_edit": True, "room": room},
    )