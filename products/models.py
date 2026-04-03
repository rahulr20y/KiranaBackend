from django.db import models
from django.contrib.auth import get_user_model
from categories.models import Category

User = get_user_model()


class Product(models.Model):
    """Product model for dealers to list products"""
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, default='kg')  # kg, liter, piece, box, etc
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    price_tiers = models.JSONField(default=list, blank=True, help_text="e.g. [{'min_quantity': 10, 'price': 90}, {'min_quantity': 50, 'price': 80}]")
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_price_for_quantity(self, quantity):
        """Returns the appropriate tier price for the given quantity"""
        if not self.price_tiers:
            return self.price
        
        # Sort tiers by min_quantity descending to find the highest applicable tier
        sorted_tiers = sorted(self.price_tiers, key=lambda x: int(x['min_quantity']), reverse=True)
        for tier in sorted_tiers:
            if int(quantity) >= int(tier['min_quantity']):
                return tier['price']
        
        return self.price
    
    def update_stock(self, amount, user, reason='correction', notes=None):
        """Update stock and log the change"""
        self.stock_quantity += int(amount)
        self.save()
        StockAuditLog.objects.create(
            product=self,
            user=user,
            change_amount=amount,
            new_stock=self.stock_quantity,
            reason=reason,
            notes=notes
        )
        return self.stock_quantity

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['dealer']),
            models.Index(fields=['category']),
            models.Index(fields=['is_available']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.dealer.get_full_name()}"


class ProductReview(models.Model):
    """Product review model"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_reviews'
        unique_together = ['product', 'reviewer']
    
    def __str__(self):
        return f"{self.product.name} - {self.rating} stars"

class StockAuditLog(models.Model):
    """Log for tracking stock changes with accountability"""
    MODIFICATION_TYPES = (
        ('restock', 'Restocking'),
        ('sale', 'Sale / Order'),
        ('return', 'Return / Credit'),
        ('correction', 'Inventory Correction'),
        ('initial', 'Initial Stock'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    change_amount = models.IntegerField()
    new_stock = models.IntegerField()
    reason = models.CharField(max_length=50, choices=MODIFICATION_TYPES, default='restock')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stock_audit_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name}: {self.change_amount} ({self.reason})"
