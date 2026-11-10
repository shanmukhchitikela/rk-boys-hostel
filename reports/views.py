import csv
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from residents.models import Resident
from rooms.models import Room

@staff_member_required
def index(request):
    status_filter = request.GET.get('resident_status', 'active')
    
    if status_filter == 'active':
        residents = Resident.objects.filter(is_active=True).select_related('room')
    elif status_filter == 'inactive':
        residents = Resident.objects.filter(is_active=False).select_related('room')
    else:
        residents = Resident.objects.all().select_related('room')

    total_rooms = Room.objects.count()
    total_residents = Resident.objects.filter(is_active=True).count()

    context = {
        'residents': residents,
        'total_rooms': total_rooms,
        'total_residents': total_residents,
        'current_status': status_filter,
    }
    return render(request, 'reports/index.html', context)

@staff_member_required
def residents_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="residents_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Full Name', 'Phone', 'Emergency Contact', 'ID Proof Number', 'Room', 'Joining Date', 'Status'])

    residents = Resident.objects.all().select_related('room')
    for resident in residents:
        room_num = resident.room.room_number if resident.room else 'Unassigned'
        writer.writerow([
            resident.full_name,
            resident.phone,
            resident.emergency_contact,
            resident.id_proof_number,
            room_num,
            resident.joining_date,
            'Active' if resident.is_active else 'Inactive'
        ])

    return response

@staff_member_required
def rooms_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rooms_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Room Number', 'Capacity', 'Current Occupants', 'Available Beds'])

    rooms = Room.objects.all()
    for room in rooms:
        active_occupants = room.residents.filter(is_active=True).count()
        available_beds = room.capacity - active_occupants
        writer.writerow([
            room.room_number,
            room.capacity,
            active_occupants,
            available_beds
        ])

    return response

@staff_member_required
def charges_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="charges_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Resident Name', 'Room', 'Agreed Monthly Fee', 'Joining Date', 'Status'])

    residents = Resident.objects.all().select_related('room')
    for resident in residents:
        room_num = resident.room.room_number if resident.room else 'Unassigned'
        monthly_fee = getattr(resident, 'agreed_monthly_fee', 0)
        writer.writerow([
            resident.full_name,
            room_num,
            monthly_fee,
            resident.joining_date,
            'Active' if resident.is_active else 'Inactive'
        ])

    return response

@staff_member_required
def payments_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payments_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Resident Name', 'Room', 'Agreed Monthly Fee', 'Joining Date', 'Status'])

    residents = Resident.objects.all().select_related('room')
    for resident in residents:
        room_num = resident.room.room_number if resident.room else 'Unassigned'
        monthly_fee = getattr(resident, 'agreed_monthly_fee', 0)
        writer.writerow([
            resident.full_name,
            room_num,
            monthly_fee,
            resident.joining_date,
            'Active' if resident.is_active else 'Inactive'
        ])

    return response

@staff_member_required
def advances_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="advances_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Resident Name', 'Room', 'Agreed Monthly Fee', 'Joining Date', 'Status'])

    residents = Resident.objects.all().select_related('room')
    for resident in residents:
        room_num = resident.room.room_number if resident.room else 'Unassigned'
        monthly_fee = getattr(resident, 'agreed_monthly_fee', 0)
        writer.writerow([
            resident.full_name,
            room_num,
            monthly_fee,
            resident.joining_date,
            'Active' if resident.is_active else 'Inactive'
        ])

    return response