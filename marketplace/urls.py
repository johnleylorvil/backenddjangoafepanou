# marketplace/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StoreViewSet, ProductCategoryViewSet, ProductTagViewSet, ProductViewSet,
    AddressViewSet, CartViewSet, OrderViewSet, VendorOrderViewSet
)

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'categories', ProductCategoryViewSet, basename='category')
router.register(r'tags', ProductTagViewSet, basename='tag')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'vendor/orders', VendorOrderViewSet, basename='vendor-order')

app_name = 'marketplace'

urlpatterns = [
    path('', include(router.urls)),
]