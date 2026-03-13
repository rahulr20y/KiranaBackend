from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Shopkeeper
from .serializers import ShopkeeperSerializer, ShopkeeperListSerializer


class ShopkeeperViewSet(viewsets.ModelViewSet):
    """ViewSet for managing shopkeepers"""
    queryset = Shopkeeper.objects.select_related('user')
    serializer_class = ShopkeeperSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['shop_name', 'business_type']
    ordering_fields = ['rating', 'total_orders', 'created_at']
    ordering = ['-total_orders']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ShopkeeperListSerializer
        return ShopkeeperSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated()])
    def my_profile(self, request):
        """Get current shopkeeper's profile"""
        try:
            shopkeeper = request.user.shopkeeper_profile
            serializer = ShopkeeperSerializer(shopkeeper)
            return Response(serializer.data)
        except Shopkeeper.DoesNotExist:
            return Response(
                {'error': 'Shopkeeper profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated()])
    def create_profile(self, request):
        """Create shopkeeper profile"""
        if hasattr(request.user, 'shopkeeper_profile'):
            return Response(
                {'error': 'Shopkeeper profile already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shopkeeper = Shopkeeper.objects.create(user=request.user, **request.data)
        serializer = ShopkeeperSerializer(shopkeeper)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated()])
    def update_profile(self, request):
        """Update shopkeeper profile"""
        try:
            shopkeeper = request.user.shopkeeper_profile
            serializer = ShopkeeperSerializer(shopkeeper, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Shopkeeper.DoesNotExist:
            return Response(
                {'error': 'Shopkeeper profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated()])
    def follow_dealer(self, request, pk=None):
        """Follow a dealer"""
        try:
            shopkeeper = request.user.shopkeeper_profile
            dealer_id = request.data.get('dealer_id')
            if dealer_id:
                shopkeeper.preferred_dealers.add(dealer_id)
                return Response({'message': 'Dealer followed'})
            return Response({'error': 'dealer_id required'}, status=status.HTTP_400_BAD_REQUEST)
        except Shopkeeper.DoesNotExist:
            return Response(
                {'error': 'Shopkeeper profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated()])
    def unfollow_dealer(self, request, pk=None):
        """Unfollow a dealer"""
        try:
            shopkeeper = request.user.shopkeeper_profile
            dealer_id = request.data.get('dealer_id')
            if dealer_id:
                shopkeeper.preferred_dealers.remove(dealer_id)
                return Response({'message': 'Dealer unfollowed'})
            return Response({'error': 'dealer_id required'}, status=status.HTTP_400_BAD_REQUEST)
        except Shopkeeper.DoesNotExist:
            return Response(
                {'error': 'Shopkeeper profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated()])
    def my_followed_dealers(self, request):
        """Get shopkeeper's followed dealers"""
        try:
            shopkeeper = request.user.shopkeeper_profile
            dealers = shopkeeper.preferred_dealers.all()
            from dealers.serializers import DealerListSerializer
            serializer = DealerListSerializer(dealers, many=True)
            return Response(serializer.data)
        except Shopkeeper.DoesNotExist:
            return Response(
                {'error': 'Shopkeeper profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
