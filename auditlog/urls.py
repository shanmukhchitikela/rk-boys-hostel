from django.urls import path
from . import views

app_name = 'auditlog'

urlpatterns = [
    path('settings/', views.settings_page, name='settings'),
    path('history/', views.history_page, name='history'),
]