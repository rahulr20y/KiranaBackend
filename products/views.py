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
        user = self.request.user
        if user.is_authenticated and user.user_type == 'dealer':
            product = serializer.save(dealer=user)
            # Log initial stock
            from .models import StockAuditLog
            StockAuditLog.objects.create(
                product=product,
                user=user,
                change_amount=product.stock_quantity,
                new_stock=product.stock_quantity,
                reason='initial',
                notes='Product initially added to catalog'
            )
        else:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only dealers can create products')
    
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
        dealer_id = request.query_params.get('dealer_id') or request.query_params.get('dealer')
        if dealer_id:
            products = Product.objects.filter(dealer_id=dealer_id)
            serializer = self.get_serializer(products, many=True)
            return Response(serializer.data)
        return Response({'error': 'dealer_id or dealer parameter required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def variance_report(self, request):
        """Get inventory variance report for the current dealer"""
        if request.user.user_type != 'dealer':
            return Response({'error': 'Unauthorized'}, status=403)
            
        from .models import StockAuditLog, Product
        from django.db.models import Sum, Count, Q
        import datetime
        
        last_30_days = datetime.date.today() - datetime.timedelta(days=30)
        
        # 1. Overall Movement by Reason
        movements = StockAuditLog.objects.filter(
            product__dealer=request.user,
            created_at__date__gte=last_30_days
        ).values('reason').annotate(
            total_change=Sum('change_amount'),
            record_count=Count('id')
        )
        
        # 2. Daily Movement Trend
        from django.db.models.functions import TruncDate
        trends = StockAuditLog.objects.filter(
            product__dealer=request.user,
            created_at__date__gte=last_30_days
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            gains=Sum('change_amount', filter=Q(change_amount__gt=0)),
            losses=Sum('change_amount', filter=Q(change_amount__lt=0))
        ).order_by('date')
        
        # 3. Top Changed Products (Losses - primarily sales)
        top_losses = StockAuditLog.objects.filter(
            product__dealer=request.user,
            change_amount__lt=0,
            created_at__date__gte=last_30_days
        ).values('product__name').annotate(
            total_loss=Sum('change_amount')
        ).order_by('total_loss')[:5]

        return Response({
            'movements': list(movements),
            'trends': list(trends),
            'top_losses': list(top_losses),
            'period': 'Last 30 Days'
        })

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def audit_logs(self, request, pk=None):
        """Get inventory audit logs for a product"""
        product = self.get_object()
        # Verify dealer ownership or staff authorization
        is_owner = product.dealer == request.user
        if not is_owner and request.user.user_type == 'dealer_staff':
            if request.user.staff_profile.dealer.user != product.dealer:
                return Response({'error': 'Not authorized'}, status=403)
        elif not is_owner:
             return Response({'error': 'Not authorized'}, status=403)
             
        logs = product.audit_logs.all().order_by('-created_at')
        return Response([{
            'id': log.id,
            'user': log.user.username if log.user else 'System',
            'change': log.change_amount,
            'new_stock': log.new_stock,
            'reason': log.reason,
            'notes': log.notes,
            'date': log.created_at
        } for log in logs])

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_stock(self, request, pk=None):
        """Update stock with audit logging"""
        product = self.get_object()
        amount = request.data.get('amount')
        reason = request.data.get('reason', 'correction')
        notes = request.data.get('notes', '')
        
        if amount is None:
            return Response({'error': 'Amount is required'}, status=400)
            
        try:
            # Re-use the model method
            new_stock = product.update_stock(amount, request.user, reason, notes)
            return Response({
                'id': product.id,
                'name': product.name,
                'new_stock': new_stock,
                'message': 'Stock updated successfully'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=400)
