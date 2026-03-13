from django.db import models
from django.contrib.auth import get_user_model
from categories.models import Category

User = get_user_model()


class Product(models.Model):
    """Product model for dealers to list products"""
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50, default='kg')  # kg, liter, piece, box, etc
    stock_quantity = models.IntegerField(default=0)
    image = models.ImageField(upload_to='product_images/')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
