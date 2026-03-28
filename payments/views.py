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
