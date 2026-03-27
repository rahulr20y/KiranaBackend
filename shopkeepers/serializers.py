from rest_framework import serializers
from .models import Shopkeeper
from users.serializers import UserSerializer
from orders.models import Order
from django.db.models import Sum


class ShopkeeperSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    preferred_dealers_count = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Shopkeeper
        fields = [
            'id', 'user', 'shop_name', 'shop_image', 'business_type',
            'employees_count', 'monthly_budget', 'preferred_dealers_count',
            'rating', 'total_orders', 'total_spent', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_preferred_dealers_count(self, obj):
        return obj.preferred_dealers.count()

    def get_total_orders(self, obj):
        return Order.objects.filter(shopkeeper=obj.user).count()

    def get_total_spent(self, obj):
        result = Order.objects.filter(shopkeeper=obj.user).aggregate(total=Sum('net_amount'))
        return float(result['total'] or 0)

    def get_rating(self, obj):
        # Default dynamic rating for shopkeepers based on activity
        return obj.rating if obj.rating > 0 else 5.0


class ShopkeeperListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Shopkeeper
        fields = [
            'id', 'user_name', 'shop_name', 'business_type',
            'rating', 'total_orders', 'is_verified'
        ]
