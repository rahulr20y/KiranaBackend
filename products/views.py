from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Product, ProductReview
from .serializers import ProductSerializer, ProductDetailSerializer, ProductReviewSerializer


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet for managing products"""
    queryset = Product.objects.select_related('dealer', 'category')
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'category__name']
    ordering_fields = ['price', 'created_at', 'stock_quantity']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        """Create product as the current dealer"""
        if self.request.user.user_type == 'dealer':
            serializer.save(dealer=self.request.user)
        else:
            return Response(
                {'error': 'Only dealers can create products'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_products(self, request):
        """Get products of the current dealer"""
        if request.user.user_type != 'dealer':
            return Response(
                {'error': 'Only dealers can view their products'},
                status=status.HTTP_403_FORBIDDEN
            )
        # Use dealer_id explicitly to avoid any lazy object identity issues
        products = Product.objects.filter(dealer_id=request.user.id)
        serializer = self.get_serializer(products, many=True)
        return Response({
            "results": serializer.data,
            "debug": {
                "user_id": request.user.id,
                "username": request.user.username,
                "user_type": request.user.user_type,
                "count": products.count()
            }
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_review(self, request, pk=None):
        """Add a review to a product"""
        product = self.get_object()
        serializer = ProductReviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(product=product, reviewer=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response(
                    {'error': 'You have already reviewed this product'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all reviews for a product"""
        product = self.get_object()
        reviews = product.reviews.all()
        serializer = ProductReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Filter products by category"""
        category = request.query_params.get('category')
        if category:
            products = Product.objects.filter(category__slug=category)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'Category parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def by_dealer(self, request):
        """Filter products by dealer"""
        dealer_id = request.query_params.get('dealer_id')
        if dealer_id:
            products = Product.objects.filter(dealer_id=dealer_id)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'dealer_id parameter required'}, status=status.HTTP_400_BAD_REQUEST)
