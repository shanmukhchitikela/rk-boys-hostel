import csv
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    return render(request, 'reports/index.html')

@login_required
def residents_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="residents.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Room', 'Status'])
    return response

@login_required
def rooms_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="rooms.csv"'
    writer = csv.writer(response)
    writer.writerow(['Room Number', 'Capacity', 'Occupied'])
    return response