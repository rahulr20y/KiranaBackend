from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DealerBroadcast, UserNotification
from .serializers import DealerBroadcastSerializer, UserNotificationSerializer

class BroadcastViewSet(viewsets.ModelViewSet):
    """ViewSet for managing dealer broadcasts"""
    queryset = DealerBroadcast.objects.all()
    serializer_class = DealerBroadcastSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 'dealer':
            return DealerBroadcast.objects.filter(dealer=user)
        elif user.user_type == 'shopkeeper':
            # Shopkeeper sees broadcasts from dealers they follow
            # Safely check if shopkeeper_profile exists
            if hasattr(user, 'shopkeeper_profile'):
                dealer_ids = user.shopkeeper_profile.preferred_dealers.values_list('id', flat=True)
                return DealerBroadcast.objects.filter(dealer_id__in=dealer_ids)
        return DealerBroadcast.objects.none()

    def perform_create(self, serializer):
        if self.request.user.user_type == 'dealer':
            serializer.save(dealer=self.request.user)
        else:
            raise PermissionError("Only dealers can create broadcasts")

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """Get latest broadcasts for shopkeepers or latest sent for dealers"""
        broadcasts = self.get_queryset()[:10]
        serializer = self.get_serializer(broadcasts, many=True)
        return Response(serializer.data)

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing personal user notifications"""
    queryset = UserNotification.objects.all()
    serializer_class = UserNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserNotification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'status': 'all marked as read'})
