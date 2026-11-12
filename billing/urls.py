from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('charges/', views.charge_list, name='charge_list'),
    path('charges/create/', views.charge_create, name='charge_create'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('paid-residents/', views.paid_residents, name='paid_residents'),
    path('attention-residents/', views.attention_residents, name='attention_residents'),
]