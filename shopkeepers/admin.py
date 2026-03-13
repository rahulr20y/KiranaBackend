from django.contrib import admin
from .models import Shopkeeper

@admin.register(Shopkeeper)
class ShopkeeperAdmin(admin.ModelAdmin):
    list_display = ['shop_name', 'user', 'rating', 'total_orders', 'is_verified']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['shop_name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']