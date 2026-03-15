from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

# Global API Router
router = routers.DefaultRouter()

# Register ViewSets
from users.views import UserViewSet
from products.views import ProductViewSet
from dealers.views import DealerViewSet
from shopkeepers.views import ShopkeeperViewSet
from orders.views import OrderViewSet
from categories.views import CategoryViewSet

router.register(r'users', UserViewSet, basename='user')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'dealers', DealerViewSet, basename='dealer')
router.register(r'shopkeepers', ShopkeeperViewSet, basename='shopkeeper')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/docs/', include_docs_urls(title='Kirana API')),
    
    # Standalone API Views (Login, Register, Logout)
    path('api/v1/users/', include('users.urls')),
    
    # Consolidated API v1
    path('api/v1/', include(router.urls)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
