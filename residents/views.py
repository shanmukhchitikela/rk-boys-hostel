from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Resident
from .forms import ResidentForm
from rooms.utils import natural_resident_key

def resident_list(request):
    residents = list(Resident.objects.all().select_related('room'))
    residents.sort(key=natural_resident_key)
    return render(request, 'residents/resident_list.html', {'residents': residents})

def resident_create(request):
    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES)
        if form.is_valid():
            resident = form.save()
            messages.success(request, f"Resident '{resident.full_name}' added successfully!")
            return redirect('residents:resident_list')
    else:
        initial = {}
        room_id = request.GET.get('room')
        if room_id:
            initial['room'] = room_id
        form = ResidentForm(initial=initial)
    return render(request, 'residents/resident_form.html', {'form': form, 'is_edit': False})

def resident_detail(request, pk):
    resident = get_object_or_404(Resident.objects.select_related('room'), pk=pk)
    return render(request, 'residents/resident_detail.html', {'resident': resident})

def resident_edit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        form = ResidentForm(request.POST, request.FILES, instance=resident)
        if form.is_valid():
            form.save()
            messages.success(request, f"Resident '{resident.full_name}' updated successfully!")
            return redirect('residents:resident_list')
    else:
        form = ResidentForm(instance=resident)
    return render(request, 'residents/resident_form.html', {'form': form, 'resident': resident, 'is_edit': True})

def resident_delete(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        name = resident.full_name
        resident.delete()
        messages.success(request, f"Resident '{name}' deleted successfully!")
        return redirect('residents:resident_list')
    return render(request, 'residents/resident_confirm_delete.html', {'resident': resident})
