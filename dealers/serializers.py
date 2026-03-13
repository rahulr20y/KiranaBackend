from rest_framework import serializers
from .models import Dealer, DealerDocument
from users.serializers import UserSerializer


class DealerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DealerDocument
        fields = ['id', 'document_type', 'document_file', 'is_verified', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class DealerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    documents = DealerDocumentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Dealer
        fields = [
            'id', 'user', 'business_name', 'business_license', 'gst_number',
            'business_category', 'years_in_business', 'total_products',
            'rating', 'total_orders', 'is_verified', 'documents', 'created_at'
        ]
        read_only_fields = ['id', 'total_products', 'rating', 'total_orders', 'created_at']


class DealerListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Dealer
        fields = [
            'id', 'user_name', 'business_name', 'business_category',
            'rating', 'total_products', 'total_orders', 'is_verified'
        ]
