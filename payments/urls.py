from django.urls import path
from .views import PaymentViewSet

urlpatterns = [
    path('create_razorpay_order/', PaymentViewSet.as_view({'post': 'create_razorpay_order'})),
    path('verify/', PaymentViewSet.as_view({'post': 'verify_razorpay_payment'})),
    path('summary/', PaymentViewSet.as_view({'get': 'summary'})),
    path('detailed_ledger/', PaymentViewSet.as_view({'get': 'detailed_ledger'})),
]
