from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from residents.models import Resident

class Charge(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('PARTIAL', 'Partially Paid'),
        ('OVERDUE', 'Overdue'),
    )

    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='charges')
    title = models.CharField(max_length=200, default="Monthly Rent")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resident.full_name} - {self.title} - ₹{self.amount}"

    @property
    def period(self):
        return self.due_date.strftime("%B %Y") if self.due_date else self.title

    @property
    def paid_amount(self):
        total = self.payments.aggregate(total=Sum('amount_paid'))['total']
        return total or Decimal('0.00')

    @property
    def pending_amount(self):
        return max(Decimal('0.00'), self.amount - self.paid_amount)

    @property
    def status_label(self):
        return self.get_status_display()

class Payment(models.Model):
    charge = models.ForeignKey(Charge, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=50, default="UPI/Cash")

    def __str__(self):
        return f"Payment ₹{self.amount_paid} for {self.charge.resident.full_name}"

    @property
    def receipt_number(self):
        return f"REC-{self.id:05d}"
