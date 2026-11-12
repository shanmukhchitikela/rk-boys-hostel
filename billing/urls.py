from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.charge_list, name='billing_root'),
    path('charges/', views.charge_list, name='charge_list'),
    path('charges/create/', views.charge_create, name='charge_create'),
    path('charges/<int:pk>/', views.charge_detail, name='charge_detail'),
    path('charges/<int:pk>/payment/', views.payment_create, name='payment_create'),
    path('payments/', views.payment_history, name='payment_history'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('paid-residents/', views.paid_residents, name='paid_residents'),
    path('attention-residents/', views.attention_residents, name='attention_residents'),
]
