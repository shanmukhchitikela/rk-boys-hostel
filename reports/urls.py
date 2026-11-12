from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.index, name='index'),
    path('residents/csv/', views.residents_csv, name='residents_csv'),
    path('rooms/csv/', views.rooms_csv, name='rooms_csv'),
]