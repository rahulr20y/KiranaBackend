from rest_framework import serializers
from .models import Product, ProductReview
from categories.models import Category
from users.serializers import UserSerializer
from categories.serializers import CategorySerializer


class ProductReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = ['id', 'product', 'reviewer', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    dealer_name = serializers.CharField(source='dealer.get_full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    
    image = serializers.ImageField(required=False, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False, allow_null=True)

    def validate_category(self, value):
        if value == '':
            return None
        return value

    class Meta:
        model = Product
        fields = [
            'id', 'dealer', 'dealer_name', 'category', 'category_name',
            'name', 'description', 'price', 'unit', 'stock_quantity',
            'image', 'is_available', 'average_rating', 'review_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'dealer', 'created_at', 'updated_at']
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return sum(r.rating for r in reviews) / reviews.count()
        return 0
    
    def get_review_count(self, obj):
        return obj.reviews.count()


class ProductDetailSerializer(serializers.ModelSerializer):
    dealer = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'dealer', 'category', 'name', 'description', 'price',
            'unit', 'stock_quantity', 'image', 'is_available',
            'reviews', 'average_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            return sum(r.rating for r in reviews) / reviews.count()
        return 0
