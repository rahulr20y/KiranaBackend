from django.contrib import admin
from .models import Product, ProductReview

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'dealer', 'category', 'price', 'stock_quantity', 'is_available']
    list_filter = ['is_available', 'category', 'created_at']
    search_fields = ['name', 'dealer__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'reviewer', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'reviewer__username']