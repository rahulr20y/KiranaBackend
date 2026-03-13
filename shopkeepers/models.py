from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Shopkeeper(models.Model):
    """Shopkeeper profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shopkeeper_profile')
    shop_name = models.CharField(max_length=200)
    shop_image = models.ImageField(upload_to='shop_images/', blank=True, null=True)
    business_type = models.CharField(max_length=100)
    employees_count = models.IntegerField(default=1)
    monthly_budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    preferred_dealers = models.ManyToManyField(User, related_name='shopkeeper_followers', blank=True)
    rating = models.FloatField(default=0)
    total_orders = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopkeepers'
        verbose_name = 'Shopkeeper'
        verbose_name_plural = 'Shopkeepers'
    
    def __str__(self):
        return f"{self.shop_name} - {self.user.get_full_name()}"
