from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, RegisterAPIView, LoginAPIView, LogoutAPIView, GoogleAuthAPIView

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginAPIView.as_view(), name='login'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('google-auth/', GoogleAuthAPIView.as_view(), name='google-auth'),
    path('', include(router.urls)),
]
