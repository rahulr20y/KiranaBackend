from rest_framework import serializers
from .models import DealerBroadcast, UserNotification

class DealerBroadcastSerializer(serializers.ModelSerializer):
    dealer_name = serializers.CharField(source='dealer.get_full_name', read_only=True)
    business_name = serializers.CharField(source='dealer.dealer_profile.business_name', read_only=True)
    
    class Meta:
        model = DealerBroadcast
        fields = ['id', 'dealer', 'dealer_name', 'business_name', 'title', 'message', 'notification_type', 'created_at']
        read_only_fields = ['id', 'dealer', 'created_at']

class UserNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
