from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Payment(models.Model):
    """Record of a payment made by a shopkeeper to a dealer"""
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    shopkeeper = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_made')
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments_received')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_payments')
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='upi')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="Reference ID for digital payments")
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment of {self.amount} from {self.shopkeeper.username} to {self.dealer.username}"
