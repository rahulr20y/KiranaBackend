from django.contrib import admin
from .models import Dealer, DealerDocument

@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'rating', 'total_products', 'is_verified']
    list_filter = ['is_verified', 'is_banned', 'created_at']
    search_fields = ['business_name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(DealerDocument)
class DealerDocumentAdmin(admin.ModelAdmin):
    list_display = ['dealer', 'document_type', 'is_verified', 'uploaded_at']
    list_filter = ['is_verified', 'document_type']
    search_fields = ['dealer__business_name']