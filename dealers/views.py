from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Dealer, DealerDocument, DealerStaff
from .serializers import DealerSerializer, DealerListSerializer, DealerDocumentSerializer, DealerStaffSerializer
from users.models import User
from django.db import transaction


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
        if request.user.user_type not in ['dealer', 'dealer_staff']:
            return Response(
                {'error': 'User is not a dealer or dealer staff'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            if request.user.user_type == 'dealer_staff':
                dealer = request.user.staff_profile.dealer
            else:
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def manage_staff(self, request):
        """List all staff members for this dealer"""
        if request.user.user_type != 'dealer':
            return Response({"error": "Only dealers can manage staff"}, status=403)
            
        staff = request.user.dealer_profile.staff_members.all()
        serializer = DealerStaffSerializer(staff, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def add_staff(self, request):
        """Invite/Add a new staff member"""
        if request.user.user_type != 'dealer':
            return Response({"error": "Only dealers can add staff"}, status=403)
            
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password', 'Staff@123')
        role = request.data.get('role', 'Delivery Manager')
        
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=400)
            
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='dealer_staff',
                first_name=request.data.get('first_name', ''),
                last_name=request.data.get('last_name', '')
            )
            
            staff = DealerStaff.objects.create(
                user=user,
                dealer=request.user.dealer_profile,
                role=role,
                can_manage_orders=request.data.get('can_manage_orders', True),
                can_manage_inventory=request.data.get('can_manage_inventory', True),
                can_view_analytics=request.data.get('can_view_analytics', False)
            )
            
        serializer = DealerStaffSerializer(staff)
        return Response(serializer.data, status=201)
