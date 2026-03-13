from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShopkeeperViewSet

router = DefaultRouter()
router.register(r'', ShopkeeperViewSet, basename='shopkeeper')

urlpatterns = [
    path('', include(router.urls)),
]
