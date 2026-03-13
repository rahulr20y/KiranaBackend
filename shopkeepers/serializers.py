from rest_framework import serializers
from .models import Shopkeeper
from users.serializers import UserSerializer


class ShopkeeperSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    preferred_dealers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Shopkeeper
        fields = [
            'id', 'user', 'shop_name', 'shop_image', 'business_type',
            'employees_count', 'monthly_budget', 'preferred_dealers_count',
            'rating', 'total_orders', 'total_spent', 'is_verified', 'created_at'
        ]
        read_only_fields = ['id', 'rating', 'total_orders', 'total_spent', 'created_at']
    
    def get_preferred_dealers_count(self, obj):
        return obj.preferred_dealers.count()


class ShopkeeperListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Shopkeeper
        fields = [
            'id', 'user_name', 'shop_name', 'business_type',
            'rating', 'total_orders', 'is_verified'
        ]
