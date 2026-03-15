from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'phone_number', 'profile_picture', 'address',
            'city', 'state', 'postal_code', 'country', 'is_verified',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'user_type', 'phone_number'
        ]
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password': 'Passwords do not match'})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user_type = validated_data.get('user_type')
        
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        
        # Automatically create profile based on user_type
        if user_type == 'dealer':
            from dealers.models import Dealer
            Dealer.objects.create(
                user=user,
                business_name=f"{user.first_name}'s Business" if user.first_name else f"{user.username}'s Business",
                business_license=f"LICENSE-{user.id}-{user.username[:5]}",
                business_category="General"
            )
        elif user_type == 'shopkeeper':
            from shopkeepers.models import Shopkeeper
            Shopkeeper.objects.create(
                user=user,
                shop_name=f"{user.first_name}'s Shop" if user.first_name else f"{user.username}'s Shop",
                business_type="Retail"
            )
            
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'phone_number', 'profile_picture', 'address',
            'city', 'state', 'postal_code', 'country', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
