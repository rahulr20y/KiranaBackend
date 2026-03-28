from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class DealerBroadcast(models.Model):
    """Broadcast messages from dealers to their followers"""
    dealer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broadcasts')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='info') # info, success, warning, alert
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'dealer_broadcasts'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} from {self.dealer.get_full_name()}"

class UserNotification(models.Model):
    """Personalized notifications for any user (shopkeeper or dealer)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='info') # info, low_stock, order_update
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.message[:20]}..."
