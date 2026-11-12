from django.db.models.signals import post_save
from django.dispatch import receiver
from billing.models import Charge, Payment

@receiver(post_save, sender=Payment)
def log_payment(sender, instance, created, **kwargs):
    if created:
        print(f"AuditLog: Payment of ₹{instance.amount_paid} recorded for {instance.charge.resident.full_name}")

@receiver(post_save, sender=Charge)
def log_charge(sender, instance, created, **kwargs):
    if created:
        print(f"AuditLog: Charge of ₹{instance.amount} created for {instance.resident.full_name}")py manage.py makemigrations billing