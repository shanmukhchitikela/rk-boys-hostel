from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Room
from .forms import RoomForm

def room_list(request):
    rooms = Room.objects.all().prefetch_related('residents')
    return render(request, 'rooms/room_list.html', {'rooms': rooms})

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
