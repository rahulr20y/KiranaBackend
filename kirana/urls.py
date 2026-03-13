from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers
from rest_framework.documentation import include_docs_urls

# API Router
router = routers.DefaultRouter()

# Include app routers
from users.urls import router as users_router
from products.urls import router as products_router
from dealers.urls import router as dealers_router
from shopkeepers.urls import router as shopkeepers_router
from orders.urls import router as orders_router
from categories.urls import router as categories_router

router.registry.extend(users_router.registry)
router.registry.extend(products_router.registry)
router.registry.extend(dealers_router.registry)
router.registry.extend(shopkeepers_router.registry)
router.registry.extend(orders_router.registry)
router.registry.extend(categories_router.registry)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/docs/', include_docs_urls(title='Kirana API')),
    
    # API Routes
    path('api/v1/', include(router.urls)),
    
    # App-specific URLs
    path('api/v1/users/', include('users.urls')),
    path('api/v1/products/', include('products.urls')),
    path('api/v1/dealers/', include('dealers.urls')),
    path('api/v1/shopkeepers/', include('shopkeepers.urls')),
    path('api/v1/orders/', include('orders.urls')),
    path('api/v1/categories/', include('categories.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
