from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_price',
            'quantity', 'unit', 'subtotal'
        ]
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shopkeeper_name = serializers.CharField(source='shopkeeper.get_full_name', read_only=True)
    dealer_name = serializers.CharField(source='dealer.get_full_name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'shopkeeper', 'shopkeeper_name',
            'dealer', 'dealer_name', 'status', 'payment_status',
            'total_amount', 'discount', 'net_amount', 'shipping_address',
            'notes', 'delivery_otp', 'items', 'created_at', 'updated_at', 'delivered_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at', 'delivered_at'
        ]


class OrderCreateSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    items = OrderItemSerializer(many=True)
    shipping_address = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Order must contain at least one item')
        return value


class OrderListSerializer(serializers.ModelSerializer):
    dealer_name = serializers.CharField(source='dealer.get_full_name', read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'dealer_name', 'status', 'payment_status',
            'net_amount', 'item_count', 'delivery_otp', 'created_at'
        ]
    
    def get_item_count(self, obj):
        return obj.items.count()
