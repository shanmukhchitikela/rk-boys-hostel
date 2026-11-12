from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Room

@login_required
def room_list(request):
    rooms = Room.objects.all()
    return render(request, 'rooms/room_list.html', {'rooms': rooms})

@login_required
def room_create(request):
    if request.method == 'POST':
        room_number = request.POST.get('room_number', '').strip()
        floor = request.POST.get('floor', 1)
        capacity = request.POST.get('capacity', 1)
        fee_val = request.POST.get('fee') or request.POST.get('monthly_fee') or 0

        # Check duplicate room number
        if Room.objects.filter(room_number=room_number).exists():
            messages.error(request, f"Room '{room_number}' already exists! Please use a different room number.")
            return render(request, 'rooms/room_form.html', {
                'room_number': room_number,
                'floor': floor,
                'capacity': capacity,
                'fee': fee_val
            })

        room = Room()
        
        # Dynamically set fields matching exact database column names
        for field in Room._meta.get_fields():
            f_name = field.name
            if f_name == 'room_number':
                setattr(room, f_name, room_number)
            elif f_name == 'floor':
                setattr(room, f_name, int(floor) if floor else 1)
            elif f_name == 'capacity':
                setattr(room, f_name, int(capacity) if capacity else 1)
            elif f_name in ['fee', 'monthly_fee', 'price']:
                setattr(room, f_name, float(fee_val) if fee_val else 0.0)

        room.save()
        messages.success(request, f"Room {room_number} created successfully!")
        return redirect('rooms:room_list')

    return render(request, 'rooms/room_form.html')

@login_required
def room_detail(request, pk):
    room = get_object_or_404(Room, pk=pk)
    return render(request, 'rooms/room_detail.html', {'room': room})

@login_required
def room_edit(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        room_number = request.POST.get('room_number', '').strip()
        floor = request.POST.get('floor', 1)
        capacity = request.POST.get('capacity', 1)
        fee_val = request.POST.get('fee') or request.POST.get('monthly_fee') or 0

        if Room.objects.filter(room_number=room_number).exclude(pk=pk).exists():
            messages.error(request, f"Room '{room_number}' already exists!")
            return render(request, 'rooms/room_form.html', {'room': room})

        for field in Room._meta.get_fields():
            f_name = field.name
            if f_name == 'room_number':
                setattr(room, f_name, room_number)
            elif f_name == 'floor':
                setattr(room, f_name, int(floor) if floor else 1)
            elif f_name == 'capacity':
                setattr(room, f_name, int(capacity) if capacity else 1)
            elif f_name in ['fee', 'monthly_fee', 'price']:
                setattr(room, f_name, float(fee_val) if fee_val else 0.0)

        room.save()
        messages.success(request, f"Room {room_number} updated successfully!")
        return redirect('rooms:room_list')

    return render(request, 'rooms/room_form.html', {'room': room})

@login_required
def room_delete(request, pk):
    room = get_object_or_404(Room, pk=pk)
    if request.method == 'POST':
        room.delete()
        messages.success(request, "Room deleted successfully!")
        return redirect('rooms:room_list')
    return render(request, 'rooms/room_confirm_delete.html', {'room': room})