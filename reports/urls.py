from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.index, name='index'),
    path('residents/csv/', views.residents_csv, name='residents_csv'),
    path('rooms/csv/', views.rooms_csv, name='rooms_csv'),
    # Drill-down reports
    path('vacancies/', views.vacancies_report, name='vacancies_report'),
    path('expected-charges/', views.expected_charges_report, name='expected_charges_report'),
    path('collected/', views.collected_report, name='collected_report'),
    path('balance/', views.balance_report, name='balance_report'),
    # Settings & Logout
    path('settings/', views.account_settings, name='account_settings'),
    path('logout/', views.logout_view, name='logout'),
]
