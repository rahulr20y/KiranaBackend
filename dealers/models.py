from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Dealer(models.Model):
    """Dealer profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer_profile')
    business_name = models.CharField(max_length=200)
    business_license = models.CharField(max_length=100, blank=True, null=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    business_category = models.CharField(max_length=100, blank=True, null=True)
    years_in_business = models.IntegerField(default=0, blank=True, null=True)
    total_products = models.IntegerField(default=0)
    rating = models.FloatField(default=0)
    total_orders = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dealers'
        verbose_name = 'Dealer'
        verbose_name_plural = 'Dealers'
    
    def __str__(self):
        return f"{self.business_name} - {self.user.get_full_name()}"


class DealerDocument(models.Model):
    """Store dealer verification documents"""
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50)  # license, gst, pan, etc
    document_file = models.FileField(upload_to='dealer_documents/')
    is_verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dealer_documents'
    
    def __str__(self):
        return f"{self.dealer.business_name} - {self.document_type}"

class DealerStaff(models.Model):
    """Staff member of a Dealer"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name='staff_members')
    role = models.CharField(max_length=50, default='Delivery Manager') # Delivery Manager, Inventory Clerk
    can_manage_orders = models.BooleanField(default=True)
    can_manage_inventory = models.BooleanField(default=True)
    can_view_analytics = models.BooleanField(default=False) # Restricted by default
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dealer_staff'
    
    def __str__(self):
        return f"{self.user.get_full_name()} (Staff of {self.dealer.business_name})"
