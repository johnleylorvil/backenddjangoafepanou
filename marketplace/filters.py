# marketplace/filters.py
from django_filters import rest_framework as filters
from .models import Product, Store, Order

class ProductFilter(filters.FilterSet):
    """
    Filtres pour les produits.
    """
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    min_price = filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = filters.CharFilter(field_name='categories__slug')
    tag = filters.CharFilter(field_name='tags__slug')
    store = filters.CharFilter(field_name='store__slug')
    product_type = filters.ChoiceFilter(choices=Product.PRODUCT_TYPE_CHOICES)
    status = filters.ChoiceFilter(choices=Product.STATUS_CHOICES)
    currency = filters.ChoiceFilter(choices=Product.CURRENCY_CHOICES)
    
    class Meta:
        model = Product
        fields = [
            'name', 'min_price', 'max_price', 'category', 
            'tag', 'store', 'product_type', 'status', 'currency'
        ]

class StoreFilter(filters.FilterSet):
    """
    Filtres pour les boutiques.
    """
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    is_active = filters.BooleanFilter()
    
    class Meta:
        model = Store
        fields = ['name', 'is_active']

class OrderFilter(filters.FilterSet):
    """
    Filtres pour les commandes.
    """
    status = filters.ChoiceFilter(choices=Order.STATUS_CHOICES)
    min_date = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    max_date = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    min_amount = filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_amount = filters.NumberFilter(field_name='total_amount', lookup_expr='lte')
    
    class Meta:
        model = Order
        fields = ['status', 'min_date', 'max_date', 'min_amount', 'max_amount']