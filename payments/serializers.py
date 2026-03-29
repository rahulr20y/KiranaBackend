from rest_framework import serializers
from .models import Payment
from users.serializers import UserSerializer

class PaymentSerializer(serializers.ModelSerializer):
    shopkeeper_name = serializers.CharField(source='shopkeeper.username', read_only=True)
    dealer_name = serializers.CharField(source='dealer.username', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'shopkeeper', 'dealer', 'amount', 'order',
            'payment_date', 'payment_method', 'status', 
            'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature',
            'transaction_id', 'notes', 'shopkeeper_name', 'dealer_name', 'order_number'
        ]
        read_only_fields = ['id', 'payment_date', 'razorpay_order_id']
