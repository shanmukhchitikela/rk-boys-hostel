from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Room
from .forms import RoomForm
from .utils import natural_room_key

def room_list(request):
    rooms = list(Room.objects.all().prefetch_related('residents'))
    rooms.sort(key=natural_room_key)

    total_capacity = sum(r.capacity for r in rooms)
    total_occupied = sum(r.active_occupants for r in rooms)
    total_vacancies = sum(r.available_beds for r in rooms)

    context = {
        'rooms': rooms,
        'total_capacity': total_capacity,
        'total_occupied': total_occupied,
        'total_vacancies': total_vacancies,
    }
    return render(request, 'rooms/room_list.html', context)

def room_create(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            room = form.save()
            messages.success(request, f"Room {room.room_number} created successfully!")
            return redirect('rooms:room_list')
    else:
        form = RoomForm()
    return render(request, 'rooms/room_form.html', {'form': form, 'is_edit': False})

def room_detail(request, pk):
    room = get_object_or_404(Room.objects.prefetch_related('residents'), pk=pk)
    return render(request, 'rooms/room_detail.html', {'room': room})

def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        form = RoomForm(request.POST, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, f"Room {room.room_number} updated successfully!")
            return redirect('rooms:room_list')
    else:
        form = RoomForm(instance=room)
    return render(request, 'rooms/room_form.html', {'form': form, 'room': room, 'is_edit': True})

def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        room_num = room.room_number
        room.delete()
        messages.success(request, f"Room {room_num} deleted successfully!")
        return redirect('rooms:room_list')
    return render(request, 'rooms/room_confirm_delete.html', {'room': room})
