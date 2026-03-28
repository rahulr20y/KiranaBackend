from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BroadcastViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'broadcasts', BroadcastViewSet, basename='broadcasts')
router.register(r'notifications', NotificationViewSet, basename='personal-notifications')

urlpatterns = [
    path('', include(router.urls)),
]
