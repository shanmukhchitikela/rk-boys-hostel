from django.urls import path
from . import views

app_name = 'residents'

urlpatterns = [
    path('', views.resident_list, name='resident_list'),
    path('create/', views.resident_create, name='resident_create'),
    path('<int:pk>/', views.resident_detail, name='resident_detail'),
    path('<int:pk>/edit/', views.resident_edit, name='resident_edit'),
    path('<int:pk>/delete/', views.resident_delete, name='resident_delete'),
]