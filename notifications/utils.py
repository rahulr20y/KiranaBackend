from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import UserNotification
from .serializers import UserNotificationSerializer

def send_user_notification(user, title, message, notification_type='info'):
    # Create DB record
    notification = UserNotification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )
    
    # Send via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "data": UserNotificationSerializer(notification).data
        }
    )
    return notification
