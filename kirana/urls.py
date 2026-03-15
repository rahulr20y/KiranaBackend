from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
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

import subprocess

def home_view(request):
    return JsonResponse({
        "status": "online",
        "message": "Kirana API is running",
        "version": "v1"
    })

def migrate_diag_view(request):
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'migrate', '--noinput'],
            capture_output=True,
            text=True
        )
        return JsonResponse({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

urlpatterns = [
    path('', home_view, name='home'),
    path('api/migrate-diag/', migrate_diag_view, name='migrate_diag'),
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    # The instruction provided a change to schema_view, but did not provide its definition or imports.
    # Reverting to original include_docs_urls for now to maintain syntactical correctness.
    path('api/docs/', include_docs_urls(title='Kirana API')),
    
    # Standalone API Views (Login, Register, Logout)
    path('api/v1/users/', include('users.urls')),
    
    # Consolidated API v1
    # The instruction provided a change to include individual app URLs instead of router.urls.
    # Applying this change as requested.
    path('api/v1/', include([
        path('products/', include('products.urls')),
        path('dealers/', include('dealers.urls')),
        path('shopkeepers/', include('shopkeepers.urls')),
        path('orders/', include('orders.urls')),
        path('categories/', include('categories.urls')),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
