from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("residents.csv", views.residents_csv, name="residents_csv"),
    path("rooms.csv", views.rooms_csv, name="rooms_csv"),
    path("charges.csv", views.charges_csv, name="charges_csv"),
    path("payments.csv", views.payments_csv, name="payments_csv"),
    path("advances.csv", views.advances_csv, name="advances_csv"),
]