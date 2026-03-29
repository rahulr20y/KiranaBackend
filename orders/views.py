from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils.text import slugify
import uuid
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderListSerializer, OrderCreateSerializer, OrderItemSerializer
from notifications.utils import send_user_notification


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
        """Create a new order and deduct stock"""
        from django.db import transaction
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            items_data = serializer.validated_data['items']
            
            # Generate unique order number
            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate totals
            total_amount = sum(float(item['subtotal']) for item in items_data)
            discount = float(serializer.validated_data.get('discount', 0))
            net_amount = total_amount - discount
            
            # Logic for dealer-initiated or shopkeeper-initiated order
            if request.user.user_type == 'dealer':
                dealer = request.user
                shopkeeper_id = request.data.get('shopkeeper_id')
                if not shopkeeper_id:
                    return Response({'error': 'shopkeeper_id is required for dealer-initiated sales'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    from shopkeepers.models import Shopkeeper
                    shopkeeper_profile = Shopkeeper.objects.get(id=shopkeeper_id)
                    shopkeeper = shopkeeper_profile.user
                except Shopkeeper.DoesNotExist:
                    # Fallback to User ID if profile PK doesn't match
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        shopkeeper = User.objects.get(id=shopkeeper_id, user_type='shopkeeper')
                    except User.DoesNotExist:
                        return Response({'error': 'Shopkeeper not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Shopkeeper-initiated order
                shopkeeper = request.user
                dealer_id = request.data.get('dealer_id')
                if not dealer_id:
                    return Response({'error': 'dealer_id is required'}, status=status.HTTP_400_BAD_REQUEST)
                try:
                    from dealers.models import Dealer
                    dealer_profile = Dealer.objects.get(id=dealer_id)
                    dealer = dealer_profile.user
                except Dealer.DoesNotExist:
                    # Fallback to User ID if profile PK doesn't match
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    try:
                        dealer = User.objects.get(id=dealer_id, user_type='dealer')
                    except User.DoesNotExist:
                        return Response({'error': 'Dealer not found'}, status=status.HTTP_404_NOT_FOUND)
            
            try:
                with transaction.atomic():
                    # Check and deduct stock
                    for item_data in items_data:
                        product = item_data['product']
                        quantity = item_data['quantity']
                        
                        if product.stock_quantity < quantity:
                            return Response(
                                {'error': f'Insufficient stock for {product.name}. Available: {product.stock_quantity}'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        
                        # Deduct stock
                        product.stock_quantity -= quantity
                        product.save()

                        # Low Stock Alert
                        if product.stock_quantity <= product.low_stock_threshold:
                            send_user_notification(
                                user=product.dealer,
                                title="Low Stock Alert! ⚠️",
                                message=f"Product '{product.name}' is running low. Current stock: {product.stock_quantity}",
                                notification_type="low_stock"
                            )

                    # Create order
                    order = Order.objects.create(
                        order_number=order_number,
                        shopkeeper=shopkeeper,
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
                    
                    # Log the stock change or update stats could go here
                    
                    # Notify Dealer about new order
                    send_user_notification(
                        user=dealer,
                        title="New Order Received! 📦",
                        message=f"New order #{order_number} for ₹{net_amount}",
                        notification_type="order_update"
                    )
                
                output_serializer = OrderSerializer(order)
                return Response(output_serializer.data, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancel an order and return stock"""
        from django.db import transaction
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
            
        try:
            with transaction.atomic():
                # Revert stock
                for item in order.items.all():
                    if item.product:
                        item.product.stock_quantity += item.quantity
                        item.product.save()
                
                order.status = 'cancelled'
                order.save()
                
                # Notify the other party
                other_party = order.dealer if request.user == order.shopkeeper else order.shopkeeper
                send_user_notification(
                    user=other_party,
                    title="Order Cancelled ❌",
                    message=f"Order #{order.order_number} has been cancelled",
                    notification_type="order_update"
                )
        except Exception as e:
            return Response(
                {'error': f'Failed to cancel order: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = OrderSerializer(order)
        return Response({
            'data': serializer.data,
            'message': 'Order cancelled successfully and stock restored'
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
        
        # Notify Shopkeeper about status update
        send_user_notification(
            user=order.shopkeeper,
            title="Order Status Updated! 🚚",
            message=f"Order #{order.order_number} is now {new_status}",
            notification_type="order_update"
        )
        
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
