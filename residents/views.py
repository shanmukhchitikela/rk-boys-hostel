from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Resident

@login_required
def resident_list(request):
    residents = Resident.objects.all()
    return render(request, 'residents/resident_list.html', {'residents': residents})

@login_required
def resident_create(request):
    # Form submission logic (existing view logic)
    return render(request, 'residents/resident_form.html')

@login_required
def resident_detail(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    return render(request, 'residents/resident_detail.html', {'resident': resident})

@login_required
def resident_edit(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    return render(request, 'residents/resident_form.html', {'resident': resident})

@login_required
def resident_delete(request, pk):
    resident = get_object_or_404(Resident, pk=pk)
    if request.method == 'POST' or request.method == 'GET':
        resident.delete()
        return redirect('residents:resident_list')
    return render(request, 'residents/resident_confirm_delete.html', {'resident': resident})