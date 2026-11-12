from django.urls import path
from . import views

app_name = 'rooms'

urlpatterns = [
    path('', views.room_list, name='room_list'),
    path('list/', views.room_list, name='list'),
    path('create/', views.room_create, name='room_create'),
    path('<int:pk>/', views.room_detail, name='room_detail'),
    path('<int:pk>/edit/', views.room_edit, name='room_edit'),
    path('<int:pk>/delete/', views.room_edit, name='room_delete'),
]