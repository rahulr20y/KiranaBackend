from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Dealer, DealerDocument
from .serializers import DealerSerializer, DealerListSerializer, DealerDocumentSerializer


class DealerViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dealers"""
    queryset = Dealer.objects.select_related('user').filter(is_banned=False)
    serializer_class = DealerSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['business_name', 'business_category']
    ordering_fields = ['rating', 'total_orders', 'created_at']
    ordering = ['-id']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return DealerListSerializer
        return DealerSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_profile(self, request):
        """Get current dealer's profile, create if it doesn't exist"""
        if request.user.user_type != 'dealer':
            return Response(
                {'error': 'User is not a dealer'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            dealer = request.user.dealer_profile
        except Dealer.DoesNotExist:
            # Lazy creation for legacy users
            dealer = Dealer.objects.create(
                user=request.user,
                business_name=f"{request.user.first_name}'s Business" if request.user.first_name else f"{request.user.username}'s Business",
                business_license=f"LICENSE-{request.user.id}-{request.user.username[:5]}",
                business_category="General"
            )
            
        serializer = DealerSerializer(dealer)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def create_profile(self, request):
        """Create dealer profile"""
        if hasattr(request.user, 'dealer_profile'):
            return Response(
                {'error': 'Dealer profile already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        dealer = Dealer.objects.create(user=request.user, **request.data)
        serializer = DealerSerializer(dealer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """Update dealer profile"""
        try:
            dealer = request.user.dealer_profile
            serializer = DealerSerializer(dealer, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Dealer.DoesNotExist:
            return Response(
                {'error': 'Dealer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_document(self, request):
        """Upload dealer verification document"""
        try:
            dealer = request.user.dealer_profile
            serializer = DealerDocumentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(dealer=dealer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Dealer.DoesNotExist:
            return Response(
                {'error': 'Dealer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_documents(self, request):
        """Get dealer's documents"""
        try:
            dealer = request.user.dealer_profile
            documents = dealer.documents.all()
            serializer = DealerDocumentSerializer(documents, many=True)
            return Response(serializer.data)
        except Dealer.DoesNotExist:
            return Response(
                {'error': 'Dealer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
