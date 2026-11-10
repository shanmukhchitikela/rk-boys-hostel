from django.urls import path
from . import views

app_name = "residents"

urlpatterns = [
    path("", views.resident_list, name="resident_list"),
    path("list/", views.resident_list, name="list"),
    path("new/", views.resident_create, name="resident_create"),
    path("create/", views.resident_create, name="create"),
    path("<int:pk>/", views.resident_detail, name="resident_detail"),
    path("<int:pk>/edit/", views.resident_edit, name="resident_edit"),
    path("<int:pk>/update/", views.resident_edit, name="edit"),
    path("<int:pk>/assign-room/", views.resident_assign_room, name="assign_room"),
    path("<int:pk>/exit/", views.resident_exit, name="exit"),
    path("<int:pk>/advance/deposit/", views.resident_advance_deposit, name="advance_deposit"),
    path("<int:pk>/advance/apply/", views.resident_advance_apply, name="advance_apply"),
]