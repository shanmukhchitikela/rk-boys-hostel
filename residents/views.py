from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Resident, RoomAssignment
from .forms import ResidentForm, RoomAssignmentForm

@staff_member_required
def resident_list(request):
    status_filter = request.GET.get('status', 'active')
    
    if status_filter == 'active':
        residents = Resident.objects.filter(is_active=True).select_related('room')
    elif status_filter == 'inactive':
        residents = Resident.objects.filter(is_active=False).select_related('room')
    else:
        residents = Resident.objects.all().select_related('room')

    context = {
        'residents': residents,
        'current_status': status_filter,
    }
    return render(request, 'residents/resident_list.html', context)

@staff_member_required
def resident_create(request):
    if request.method == 'POST':
        form = ResidentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Resident registered successfully!")
            return redirect('residents:resident_list')
    else:
        form = ResidentForm()
    
    return render(request, 'residents/resident_form.html', {'form': form, 'title': 'Add New Resident'})

@staff_member_required
def resident_edit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        form = ResidentForm(request.POST, instance=resident)
        if form.is_valid():
            form.save()
            messages.success(request, "Resident updated successfully!")
            return redirect('residents:resident_list')
    else:
        form = ResidentForm(instance=resident)
    
    return render(request, 'residents/resident_form.html', {'form': form, 'title': 'Edit Resident', 'resident': resident})

# Compatibility alias for resident_update
resident_update = resident_edit

@staff_member_required
def resident_detail(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    return render(request, 'residents/resident_detail.html', {'resident': resident})

@staff_member_required
def resident_assign_room(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        form = RoomAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.resident = resident
            assignment.save()
            messages.success(request, f"Room assigned to {resident.full_name} successfully!")
            return redirect('residents:resident_detail', pk=pk)
    else:
        form = RoomAssignmentForm(initial={'resident': resident})
    
    return render(request, 'residents/assignment_form.html', {'form': form, 'resident': resident})

@staff_member_required
def resident_exit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        resident.is_active = False
        resident.room = None
        resident.save()

        RoomAssignment.objects.filter(
            resident=resident, 
            end_date__isnull=True
        ).update(end_date=timezone.now().date())

        messages.success(request, f"{resident.full_name} checked out successfully.")
        return redirect('residents:resident_list')

    return render(request, 'residents/resident_confirm_exit.html', {'resident': resident})

@staff_member_required
def resident_advance_deposit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        messages.success(request, f"Advance deposit updated for {resident.full_name}.")
        return redirect('residents:resident_detail', pk=pk)
    
    return render(request, 'residents/advance_form.html', {'resident': resident})

@staff_member_required
def resident_advance_apply(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST':
        messages.success(request, f"Advance applied for {resident.full_name}.")
        return redirect('residents:resident_detail', pk=pk)
    
    return render(request, 'residents/advance_form.html', {'resident': resident})