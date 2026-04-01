from rest_framework import serializers
from .models import Order, OrderItem, ReturnRequest


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
    shopkeeper_name = serializers.CharField(source='shopkeeper.get_full_name', read_only=True)
    dealer_business_name = serializers.CharField(source='dealer.dealer_profile.business_name', default='N/A', read_only=True)
    shopkeeper_business_name = serializers.CharField(source='shopkeeper.shopkeeper_profile.shop_name', default='N/A', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'dealer_name', 'shopkeeper_name', 
            'dealer_business_name', 'shopkeeper_business_name',
            'status', 'payment_status', 'total_amount', 'discount', 
            'net_amount', 'items', 'item_count', 'delivery_otp', 'created_at'
        ]
    
    def get_item_count(self, obj):
        return obj.items.count()

class ReturnRequestSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='item.product_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    shopkeeper_name = serializers.CharField(source='shopkeeper.username', read_only=True)

    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'order', 'order_number', 'item', 'product_name',
            'shopkeeper', 'shopkeeper_name', 'dealer', 'reason', 
            'quantity', 'image', 'status', 'dealer_notes', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'shopkeeper', 'dealer', 'status', 'created_at', 'updated_at']
