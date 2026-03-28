from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Payment
from .serializers import PaymentSerializer
from orders.models import Order

class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments and ledger balance"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'dealer':
            return Payment.objects.filter(dealer=user)
        elif user.user_type == 'shopkeeper':
            return Payment.objects.filter(shopkeeper=user)
        return Payment.objects.none()

    def perform_create(self, serializer):
        # For shopkeepers, the 'shopkeeper' field is self
        # For dealers, the 'dealer' field is self
        user = self.request.user
        if user.user_type == 'shopkeeper':
            serializer.save(shopkeeper=user)
        elif user.user_type == 'dealer':
            serializer.save(dealer=user)

    @action(detail=False, methods=['get'])
    def detailed_ledger(self, request):
        """Get a detailed chronological list of all orders and payments (Passbook view)"""
        user = request.user
        partner_id = request.query_params.get('partner_id')
        
        if not partner_id:
            return Response({'error': 'partner_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        from users.models import User as UserModel
        partner = UserModel.objects.filter(id=partner_id).first()
        if not partner:
            return Response({'error': 'Partner not found'}, status=status.HTTP_404_NOT_FOUND)
            
        if user.user_type == 'dealer':
            dealer = user
            shopkeeper = partner
        else:
            dealer = partner
            shopkeeper = user
            
        # Get all orders
        orders = Order.objects.filter(dealer=dealer, shopkeeper=shopkeeper, status__in=['confirmed', 'shipped', 'delivered', 'pending', 'completed'])
        # Get all payments
        payments = Payment.objects.filter(dealer=dealer, shopkeeper=shopkeeper)
        
        # Merge and sort
        history = []
        for order in orders:
            history.append({
                'type': 'order',
                'id': order.id,
                'date': order.created_at,
                'amount': float(order.total_amount),
                'reference': f"Order #{order.order_number or order.id}",
                'status': order.status
            })
            
        for payment in payments:
            history.append({
                'type': 'payment',
                'id': payment.id,
                'date': payment.payment_date,
                'amount': float(payment.amount),
                'reference': f"Payment ({payment.payment_method})",
                'status': 'paid'
            })
            
        # Sort by date
        history.sort(key=lambda x: x['date'])
        
        # Calculate running balance
        running_balance = 0
        for item in history:
            if item['type'] == 'order':
                running_balance += item['amount']
            else:
                running_balance -= item['amount']
            item['balance_after'] = running_balance
            
        return Response({
            'partner': {
                'id': partner.id,
                'username': partner.username,
                'business_name': getattr(partner, 'dealer_profile').business_name if hasattr(partner, 'dealer_profile') else getattr(partner, 'shopkeeper_profile').shop_name if hasattr(partner, 'shopkeeper_profile') else partner.username
            },
            'history': history,
            'current_balance': running_balance
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of total orders, payments, and balance for current user"""
        user = request.user
        
        if user.user_type == 'dealer':
            # Balance owed to this dealer by all shopkeepers
            total_orders = Order.objects.filter(dealer=user, status__in=['confirmed', 'shipped', 'delivered', 'pending']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            total_payments = Payment.objects.filter(dealer=user).aggregate(Sum('amount'))['amount__sum'] or 0
            balance = total_orders - total_payments
            
            # Group by shopkeeper
            ledger = []
            from users.models import User as UserModel
            # Get IDs of all shopkeepers who have ever ordered from or paid this dealer
            shopkeeper_ids = set(Order.objects.filter(dealer=user).values_list('shopkeeper_id', flat=True)) | \
                             set(Payment.objects.filter(dealer=user).values_list('shopkeeper_id', flat=True))
            
            for sk_id in shopkeeper_ids:
                sk = UserModel.objects.filter(id=sk_id).first()
                if not sk: continue
                sk_orders = Order.objects.filter(dealer=user, shopkeeper=sk, status__in=['confirmed', 'shipped', 'delivered', 'pending']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
                sk_payments = Payment.objects.filter(dealer=user, shopkeeper=sk).aggregate(Sum('amount'))['amount__sum'] or 0
                ledger.append({
                    'shopkeeper_id': sk.id,
                    'shopkeeper_name': sk.username,
                    'business_name': sk.shopkeeper_profile.shop_name if hasattr(sk, 'shopkeeper_profile') else sk.username,
                    'total_orders': sk_orders,
                    'total_payments': sk_payments,
                    'balance': sk_orders - sk_payments
                })
            
            return Response({
                'my_total_receivable': balance,
                'total_orders_value': total_orders,
                'total_payments_received': total_payments,
                'ledger_by_shopkeeper': ledger
            })
            
        elif user.user_type == 'shopkeeper':
            # Balance owed by this shopkeeper to all dealers
            total_orders = Order.objects.filter(shopkeeper=user, status__in=['confirmed', 'shipped', 'delivered', 'pending']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
            total_payments = Payment.objects.filter(shopkeeper=user).aggregate(Sum('amount'))['amount__sum'] or 0
            balance = total_orders - total_payments
            
            # Group by dealer
            ledger = []
            from users.models import User as UserModel
            dealer_ids = set(Order.objects.filter(shopkeeper=user).values_list('dealer_id', flat=True)) | \
                         set(Payment.objects.filter(shopkeeper=user).values_list('dealer_id', flat=True))
            
            for d_id in dealer_ids:
                d = UserModel.objects.filter(id=d_id).first()
                if not d: continue
                d_orders = Order.objects.filter(shopkeeper=user, dealer=d, status__in=['confirmed', 'shipped', 'delivered', 'pending']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
                d_payments = Payment.objects.filter(shopkeeper=user, dealer=d).aggregate(Sum('amount'))['amount__sum'] or 0
                ledger.append({
                    'dealer_id': d.id,
                    'dealer_name': d.username,
                    'business_name': d.dealer_profile.business_name if hasattr(d, 'dealer_profile') else d.username,
                    'total_orders': d_orders,
                    'total_payments': d_payments,
                    'balance': d_orders - d_payments
                })
                
            return Response({
                'my_total_payable': balance,
                'total_purchases_value': total_orders,
                'total_payments_made': total_payments,
                'ledger_by_dealer': ledger
            })
            
        return Response({'error': 'Invalid user type'}, status=status.HTTP_400_BAD_REQUEST)
