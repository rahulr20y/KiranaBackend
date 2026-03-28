from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils.text import slugify
import uuid
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderListSerializer, OrderCreateSerializer, OrderItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing orders"""
    queryset = Order.objects.select_related('shopkeeper', 'dealer')
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['order_number', 'shopkeeper__username']
    ordering_fields = ['created_at', 'net_amount', 'status']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def get_queryset(self):
        """Filter orders based on user type"""
        user = self.request.user
        if user.user_type == 'shopkeeper':
            return Order.objects.filter(shopkeeper=user).select_related('dealer')
        elif user.user_type == 'dealer':
            return Order.objects.filter(dealer=user).select_related('shopkeeper')
        return Order.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create a new order"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            items_data = serializer.validated_data['items']
            
            # Generate unique order number
            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate totals
            total_amount = sum(float(item['subtotal']) for item in items_data)
            discount = float(serializer.validated_data.get('discount', 0))
            net_amount = total_amount - discount
            
            # Get dealer from first product in items
            # For now, we'll require dealer to be specified
            dealer_id = request.data.get('dealer_id')
            if not dealer_id:
                return Response(
                    {'error': 'dealer_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                dealer = User.objects.get(id=dealer_id, user_type='dealer')
            except User.DoesNotExist:
                return Response(
                    {'error': 'Dealer not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create order
            order = Order.objects.create(
                order_number=order_number,
                shopkeeper=request.user,
                dealer=dealer,
                total_amount=total_amount,
                discount=discount,
                net_amount=net_amount,
                shipping_address=serializer.validated_data['shipping_address'],
                notes=serializer.validated_data.get('notes', '')
            )
            
            # Create order items
            for item_data in items_data:
                OrderItem.objects.create(order=order, **item_data)
            
            output_serializer = OrderSerializer(order)
            return Response(output_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancel an order"""
        order = self.get_object()
        
        # Only shopkeeper or dealer can cancel their orders
        if order.shopkeeper != request.user and order.dealer != request.user:
            return Response(
                {'error': 'Not authorized to cancel this order'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status == 'cancelled':
            return Response(
                {'error': 'Order is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.save()
        
        serializer = OrderSerializer(order)
        return Response({
            'data': serializer.data,
            'message': 'Order cancelled successfully'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_status(self, request, pk=None):
        """Update order status (only dealer can do this)"""
        order = self.get_object()
        
        if order.dealer != request.user:
            return Response(
                {'error': 'Only dealer can update order status'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('status')
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = new_status
        order.save()
        
        serializer = OrderSerializer(order)
        return Response({
            'data': serializer.data,
            'message': f'Order status updated to {new_status}'
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_orders(self, request):
        """Get current user's orders"""
        orders = self.get_queryset()
        serializer = OrderListSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def stats(self, request):
        """Get order statistics"""
        orders = self.get_queryset()
        stats = {
            'total_orders': orders.count(),
            'pending': orders.filter(status='pending').count(),
            'confirmed': orders.filter(status='confirmed').count(),
            'shipped': orders.filter(status='shipped').count(),
            'delivered': orders.filter(status='delivered').count(),
            'cancelled': orders.filter(status='cancelled').count(),
            'total_amount': sum(float(o.net_amount) for o in orders),
        }
        return Response(stats)
