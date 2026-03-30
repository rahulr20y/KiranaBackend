from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet, ReturnRequestViewSet

router = DefaultRouter()
router.register(r'returns', ReturnRequestViewSet, basename='return-request')
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]
