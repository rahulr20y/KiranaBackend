from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils.text import slugify
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
import uuid
import random
import datetime
from django.utils import timezone
from .models import Order, OrderItem, ReturnRequest
from .serializers import OrderSerializer, OrderListSerializer, OrderCreateSerializer, OrderItemSerializer, ReturnRequestSerializer
from notifications.utils import send_user_notification
from .services import ReplenishmentService
from .route_service import RouteService


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
            return Order.objects.filter(shopkeeper=user).select_related('dealer').prefetch_related('items', 'dealer__dealer_profile')
        elif user.user_type == 'dealer':
            return Order.objects.filter(dealer=user).select_related('shopkeeper').prefetch_related('items', 'shopkeeper__shopkeeper_profile')
        return Order.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create a new order and deduct stock"""
        from django.db import transaction
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            items_data = serializer.validated_data['items']
            
            # Generate unique order number
            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            
            # Calculate totals and verify pricing
            total_amount = 0
            for item in items_data:
                product = item['product']
                qty = item['quantity']
                
                # Use tiered price logic
                correct_price = product.get_price_for_quantity(qty)
                item['product_price'] = correct_price
                item['subtotal'] = float(correct_price) * int(qty)
                total_amount += item['subtotal']
                
            discount = float(serializer.validated_data.get('discount', 0))
            net_amount = total_amount - discount
            
            # Resolve dealer and shopkeeper users
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if request.user.user_type == 'dealer':
                dealer = request.user
                shopkeeper_id = request.data.get('shopkeeper_id')
                if not shopkeeper_id:
                    return Response({'error': 'shopkeeper_id is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if it's a User ID first
                shopkeeper = User.objects.filter(id=shopkeeper_id, user_type='shopkeeper').first()
                if not shopkeeper:
                    # Try Profile ID fallback
                    from shopkeepers.models import Shopkeeper
                    shopkeeper_profile = Shopkeeper.objects.filter(id=shopkeeper_id).first()
                    if shopkeeper_profile:
                        shopkeeper = shopkeeper_profile.user
                
                if not shopkeeper:
                    return Response({'error': 'Shopkeeper not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Shopkeeper-initiated order
                shopkeeper = request.user
                dealer_id = request.data.get('dealer_id')
                if not dealer_id:
                    return Response({'error': 'dealer_id is required'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if it's a User ID first (frontend often sends Product.dealer which is a User ID)
                dealer = User.objects.filter(id=dealer_id, user_type='dealer').first()
                if not dealer:
                    # Try Profile ID fallback
                    from dealers.models import Dealer
                    dealer_profile = Dealer.objects.filter(id=dealer_id).first()
                    if dealer_profile:
                        dealer = dealer_profile.user
                
                if not dealer:
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
        
        import logging
        logger = logging.getLogger('django')
        logger.error(f"Order creation failed: {serializer.errors}")
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
        otp = request.data.get('otp')
        
        if new_status not in dict(Order.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Security: Requirement 3 - OTP-based Delivery Confirmation
        if new_status == 'delivered':
            if not order.delivery_otp:
                # Should not happen if flow is correct, but just in case
                return Response({'error': 'Delivery OTP was never generated for this order'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not otp:
                return Response({'error': 'Secure OTP is required to finalize delivery'}, status=status.HTTP_400_BAD_REQUEST)
            
            if otp != order.delivery_otp:
                return Response({'error': 'Incorrect OTP. Please ask the shopkeeper for the secure code.'}, status=status.HTTP_400_BAD_REQUEST)
            
            order.delivered_at = timezone.now()
            # Mark it as paid if it's already COD or similar? 
            # Or just update status.
            
        elif new_status == 'shipped':
            # Generate OTP when order is shipped
            if not order.delivery_otp:
                order.delivery_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                # Notify Shopkeeper about OTP
                send_user_notification(
                    user=order.shopkeeper,
                    title="Order Shipped! 🚚",
                    message=f"Order #{order.order_number} is out for delivery. Your secure OTP is {order.delivery_otp}. Share this ONLY with the delivery person.",
                    notification_type="order_update"
                )
        
        order.status = new_status
        order.save()
        
        # Generic notification (excluding shipped as it was handled above with OTP)
        if new_status != 'shipped':
            send_user_notification(
                user=order.shopkeeper,
                title=f"Order Updated! {new_status.capitalize()}",
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
        """Get advanced order statistics if user is dealer"""
        orders = self.get_queryset()
        user = request.user
        
        # Base stats (counts)
        stats = {
            'total_orders': orders.count(),
            'pending': orders.filter(status='pending').count(),
            'confirmed': orders.filter(status='confirmed').count(),
            'shipped': orders.filter(status='shipped').count(),
            'delivered': orders.filter(status='delivered').count(),
            'cancelled': orders.filter(status='cancelled').count(),
            'total_amount': orders.aggregate(total=Sum('net_amount'))['total'] or 0,
        }
        
        # Advanced Dealer Stats
        if user.user_type == 'dealer':
            # 1. Sales Trends (Last 30 days)
            last_30_days = datetime.date.today() - datetime.timedelta(days=30)
            sales_trends = orders.filter(
                created_at__date__gte=last_30_days
            ).annotate(
                date=TruncDate('created_at')
            ).values('date').annotate(
                total=Sum('net_amount'),
                count=Count('id')
            ).order_by('date')
            
            stats['sales_trends'] = list(sales_trends)
            
            # 2. Top Selling Products (Top 5)
            from .models import OrderItem
            top_products = OrderItem.objects.filter(
                order__dealer=user
            ).values(
                'product__name'
            ).annotate(
                total_qty=Sum('quantity'),
                total_revenue=Sum('subtotal')
            ).order_by('-total_revenue')[:5]
            
            stats['top_products'] = list(top_products)
            
            # 3. Inventory Summary from Products API (for convenience)
            from products.models import Product
            my_products = Product.objects.filter(dealer=user)
            stats['inventory_health'] = {
                'total_items': my_products.count(),
                'low_stock_items': my_products.filter(stock_quantity__lte=F('low_stock_threshold')).count(),
                'out_of_stock': my_products.filter(stock_quantity=0).count()
            }
            
        return Response(stats)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def suggestions(self, request):
        """AI Recommendation: Predict what shopkeeper needs based on order history"""
        from .services import ReplenishmentService
        user = request.user
        if user.user_type != 'shopkeeper':
            return Response({'error': 'Only shopkeepers can get replenishment suggestions'}, status=403)

        recommendations = ReplenishmentService.get_recommendations(user)
        
        formatted_suggestions = []
        for r in recommendations:
            formatted_suggestions.append({
                'product_id': r['product_id'],
                'name': r['product_name'],
                'price': r['price'],
                'dealer_id': r['dealer_id'],
                'dealer_name': r['dealer_name'],
                'reason': f"Usually lasts {int(r['avg_cycle_days'])} days. Order now?",
                'urgency': 'high' if r['confidence'] == 'High' else 'medium'
            })
            
        return Response(formatted_suggestions)

    @action(detail=False, methods=['get'], url_path='route-plan')
    def route_plan(self, request):
        """Get the optimized delivery sequence for a dealer's shipped orders"""
        if request.user.user_type != 'dealer':
            return Response({"error": "Only dealers can access route planning"}, status=403)
            
        try:
            manifest = RouteService.get_optimized_route(request.user)
            # Group by Pincode for clustering in UI
            clusters = {}
            for stop in manifest:
                pc = stop['pincode']
                if pc not in clusters:
                    clusters[pc] = []
                clusters[pc].append(stop)
                
            return Response({
                "manifest": manifest,
                "clusters": clusters,
                "total_stops": len(manifest),
                "generated_at": timezone.now().isoformat()
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class ReturnRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for managing damaged goods and return requests"""
    queryset = ReturnRequest.objects.all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'dealer':
            return ReturnRequest.objects.filter(dealer=user)
        elif user.user_type == 'shopkeeper':
            return ReturnRequest.objects.filter(shopkeeper=user)
        return ReturnRequest.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.user_type != 'shopkeeper':
            raise serializers.ValidationError("Only shopkeepers can raise return requests")
            
        # Verify order belongs to the shopkeeper and is delivered
        order = serializer.validated_data['order']
        if order.shopkeeper != user:
             raise serializers.ValidationError("You can only request returns for your own orders")
        
        if order.status != 'delivered':
            raise serializers.ValidationError("Returns can only be raised for orders marked as 'Delivered'")
             
        # Check quantity limits
        item = serializer.validated_data['item']
        requested_qty = serializer.validated_data['quantity']
        
        if requested_qty <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero")
            
        if requested_qty > item.quantity:
            raise serializers.ValidationError(f"Cannot return more than what was ordered ({item.quantity})")
            
        serializer.save(shopkeeper=user, dealer=order.dealer)

        
        # Notify Dealer
        send_user_notification(
            user=order.dealer,
            title="New Return Request! 📦",
            message=f"Shopkeeper {user.username} reported an issue with order #{order.order_number}",
            notification_type="order_update"
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve return and automatically credit the shopkeeper's account"""
        return_req = self.get_object()
        
        if request.user.user_type != 'dealer' or return_req.dealer != request.user:
            return Response({'error': 'Only the assigned dealer can approve this'}, status=status.HTTP_403_FORBIDDEN)
            
        if return_req.status != 'pending':
            return Response({'error': 'Only pending requests can be approved'}, status=status.HTTP_400_BAD_REQUEST)
            
        dealer_notes = request.data.get('dealer_notes', 'Approved and credited.')
        
        from django.db import transaction
        try:
            with transaction.atomic():
                return_req.status = 'approved'
                return_req.dealer_notes = dealer_notes
                return_req.save()
                
                # AUTOMATIC CREDIT: Create a payment record to reduce ledger balance
                from payments.models import Payment
                credit_amount = float(return_req.item.product_price) * int(return_req.quantity)
                
                # OPTIONAL STOCK RESTORE: If inventory is sellable, add it back to dealer's warehouse
                restore_stock = request.data.get('restore_stock', False)
                if restore_stock and return_req.item.product:
                    return_req.item.product.stock_quantity += return_req.quantity
                    return_req.item.product.save()
                    dealer_notes += f" (Stock of {return_req.quantity} units restored in inventory)"
                    return_req.dealer_notes = dealer_notes
                    return_req.save()

                Payment.objects.create(
                    shopkeeper=return_req.shopkeeper,
                    dealer=return_req.dealer,
                    amount=credit_amount,
                    order=return_req.order,
                    payment_method='return_credit',
                    status='success',
                    notes=f"Credit for Return Request #{return_req.id}: {return_req.reason}"
                )

                
                # Notify Shopkeeper
                send_user_notification(
                    user=return_req.shopkeeper,
                    title="Return Approved! ✅",
                    message=f"Your return for {return_req.item.product_name} was approved. ₹{credit_amount} was credited to your account.",
                    notification_type="order_update"
                )
        except Exception as e:
             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
             
        return Response({'status': 'Approved and credited successfully'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject return request"""
        return_req = self.get_object()
        
        if request.user.user_type != 'dealer' or return_req.dealer != request.user:
            return Response({'error': 'Only the assigned dealer can reject this'}, status=status.HTTP_403_FORBIDDEN)
            
        dealer_notes = request.data.get('dealer_notes')
        if not dealer_notes:
            return Response({'error': 'Rejection reason is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        return_req.status = 'rejected'
        return_req.dealer_notes = dealer_notes
        return_req.save()
        
        # Notify Shopkeeper
        send_user_notification(
            user=return_req.shopkeeper,
            title="Return Rejected ❌",
            message=f"Your return request for {return_req.item.product_name} was rejected by the dealer.",
            notification_type="order_update"
        )
        
        return Response({'status': 'Rejected successfully'})
