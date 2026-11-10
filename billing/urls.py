from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.charge_list, name="charge_list"),
    path("roster/paid/", views.paid_resident_roster, name="paid_residents"),
    path("roster/attention/", views.attention_residents, name="attention_residents"),
    path("charges/new/", views.charge_create, name="charge_create"),
    path("charges/<int:pk>/", views.charge_detail, name="charge_detail"),
    path("charges/<int:charge_pk>/payments/new/", views.payment_create, name="payment_create"),
    path("payments/<int:pk>/receipt/", views.payment_receipt, name="payment_receipt"),
]