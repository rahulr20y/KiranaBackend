import csv
import io
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser
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
    parser_classes = [MultiPartParser] + viewsets.ModelViewSet.parser_classes
    
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
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def bulk_import(self, request):
        """Import products from CSV"""
        if request.user.user_type != 'dealer':
            return Response(
                {'error': 'Only dealers can import products'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            products_created = 0
            errors = []
            
            for row in reader:
                try:
                    # Basic validation
                    name = row.get('name')
                    price = row.get('price')
                    stock = row.get('stock_quantity', row.get('stock', 0))
                    
                    if not name or not price:
                        errors.append(f"Skipping row: Missing name or price - {row}")
                        continue
                        
                    Product.objects.create(
                        dealer=request.user,
                        name=name,
                        description=row.get('description', ''),
                        price=price,
                        stock_quantity=stock,
                        low_stock_threshold=row.get('low_stock_threshold', 10),
                    )
                    products_created += 1
                except Exception as e:
                    errors.append(f"Error in row {row}: {str(e)}")
                    
            return Response({
                'message': f'Successfully imported {products_created} products',
                'errors': errors
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': f'Failed to process file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
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
