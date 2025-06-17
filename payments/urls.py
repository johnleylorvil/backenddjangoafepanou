# payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r'moncash', PaymentViewSet, basename='moncash')

app_name = 'payments'

urlpatterns = [
    path('', include(router.urls)),
    # URL directes pour plus de clarté
    path('moncash/create/', PaymentViewSet.as_view({'post': 'create'}), name='moncash-create'),
    path('moncash/status/', PaymentViewSet.as_view({'post': 'status'}), name='moncash-status'),
    path('moncash/callback/', PaymentViewSet.as_view({'post': 'callback'}), name='moncash-callback'),
    path('transactions/', PaymentViewSet.as_view({'get': 'transactions'}), name='transactions'),
]