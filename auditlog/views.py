from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def settings_page(request):
    return render(request, 'auditlog/settings.html')

@login_required
def history_page(request):
    return render(request, 'auditlog/history.html')