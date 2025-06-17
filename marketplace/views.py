# marketplace/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.contrib.auth.models import User

from .models import (
    Store, ProductCategory, ProductTag, Product, ProductImage, 
    Address, Cart, CartItem, Order, OrderItem
)
from .serializers import (
    StoreListSerializer, StoreDetailSerializer, StoreCreateUpdateSerializer,
    ProductCategorySerializer, ProductTagSerializer, ProductListSerializer,
    ProductDetailSerializer, ProductCreateUpdateSerializer, ProductImageSerializer,
    AddressSerializer, CartSerializer, CartItemSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer
)
from .permissions import IsOwnerOrReadOnly, IsVendor, IsStoreOwner, IsOrderOwnerOrVendor
from .filters import ProductFilter, StoreFilter, OrderFilter

class StoreViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des boutiques.
    
    list:
    Retourne la liste de toutes les boutiques actives.
    
    retrieve:
    Retourne les détails d'une boutique spécifique par slug.
    
    create:
    Crée une nouvelle boutique (vendeur seulement).
    
    update:
    Met à jour une boutique existante (propriétaire seulement).
    
    destroy:
    Supprime une boutique (propriétaire seulement).
    
    products:
    Retourne la liste des produits d'une boutique spécifique.
    """
    queryset = Store.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = StoreFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    lookup_field = 'slug'
    
    def get_permissions(self):
        """
        Définir les permissions en fonction de l'action.
        """
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, IsVendor]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsStoreOwner]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Retourne différents serializers selon l'action.
        """
        if self.action == 'list':
            return StoreListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return StoreCreateUpdateSerializer
        return StoreDetailSerializer
    
    def get_queryset(self):
        """
        Filtre les boutiques pour les utilisateurs non-vendeurs.
        """
        queryset = Store.objects.all()
        if self.action == 'list' and not (
            self.request.user.is_authenticated and 
            hasattr(self.request.user, 'profile') and 
            self.request.user.profile.is_vendor
        ):
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @action(detail=True, methods=['get'])
    def products(self, request, slug=None):
        """
        Récupère tous les produits d'une boutique spécifique.
        """
        store = self.get_object()
        
        # Filtrer les produits selon le statut de l'utilisateur
        if request.user.is_authenticated and (
            request.user == store.owner or
            (hasattr(request.user, 'profile') and request.user.profile.is_vendor)
        ):
            products = store.products.all()
        else:
            products = store.products.filter(status='available')
        
        # Appliquer la pagination
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = ProductListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

class ProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour la consultation des catégories de produits.
    """
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

class ProductTagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour la consultation des tags de produits.
    """
    queryset = ProductTag.objects.all()
    serializer_class = ProductTagSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

class ProductViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des produits.
    
    list:
    Retourne la liste des produits disponibles.
    
    retrieve:
    Retourne les détails d'un produit spécifique par slug.
    
    create:
    Crée un nouveau produit (vendeur seulement).
    
    update:
    Met à jour un produit existant (propriétaire de la boutique seulement).
    
    destroy:
    Supprime un produit (propriétaire de la boutique seulement).
    
    add_image:
    Ajoute une image à un produit (propriétaire de la boutique seulement).
    """
    queryset = Product.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    lookup_field = 'slug'
    
    def get_permissions(self):
        """
        Définir les permissions en fonction de l'action.
        """
        if self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, IsVendor]
        elif self.action in ['update', 'partial_update', 'destroy', 'add_image']:
            permission_classes = [permissions.IsAuthenticated, IsStoreOwner]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Retourne différents serializers selon l'action.
        """
        if self.action == 'list':
            return ProductListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        elif self.action == 'add_image':
            return ProductImageSerializer
        return ProductDetailSerializer
    
    def get_queryset(self):
        """
        Filtre les produits pour les utilisateurs non-vendeurs.
        """
        queryset = Product.objects.all().select_related('store').prefetch_related('categories', 'tags', 'images')
        
        # Pour les non-vendeurs, filtrer les produits disponibles
        if not (
            self.request.user.is_authenticated and 
            hasattr(self.request.user, 'profile') and 
            self.request.user.profile.is_vendor
        ):
            queryset = queryset.filter(status='available', store__is_active=True)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def add_image(self, request, slug=None):
        """
        Ajoute une image à un produit.
        """
        product = self.get_object()
        serializer = ProductImageSerializer(data=request.data)
        
        if serializer.is_valid():
            # Désactiver les autres images principales si celle-ci est principale
            if serializer.validated_data.get('is_main', False):
                product.images.filter(is_main=True).update(is_main=False)
            
            # Créer la nouvelle image
            serializer.save(product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AddressViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des adresses de l'utilisateur.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        """
        Retourne uniquement les adresses de l'utilisateur courant.
        """
        return Address.objects.filter(user=self.request.user)

class CartViewSet(viewsets.GenericViewSet):
    """
    API pour la gestion du panier de l'utilisateur.
    
    retrieve:
    Retourne le contenu du panier de l'utilisateur courant.
    
    add_item:
    Ajoute un produit au panier.
    
    update_item:
    Modifie la quantité d'un produit dans le panier.
    
    remove_item:
    Supprime un produit du panier.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """
        Retourne différents serializers selon l'action.
        """
        if self.action in ['add_item', 'update_item']:
            return CartItemSerializer
        return CartSerializer
    
    def retrieve(self, request):
        """
        Récupère ou crée le panier de l'utilisateur courant.
        """
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """
        Ajoute un produit au panier.
        """
        serializer = CartItemSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            cart_item = serializer.save()
            # Retourner le panier complet mis à jour
            cart = cart_item.cart
            return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['put'], url_path='items/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """
        Modifie la quantité d'un produit dans le panier.
        """
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cet article n'existe pas dans votre panier."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CartItemSerializer(cart_item, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # Retourner le panier complet mis à jour
            return Response(CartSerializer(cart).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['delete'], url_path='items/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """
        Supprime un produit du panier.
        """
        try:
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return Response(
                {"error": "Cet article n'existe pas dans votre panier."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        cart_item.delete()
        
        # Retourner le panier complet mis à jour
        return Response(CartSerializer(cart).data)

class OrderViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des commandes de l'utilisateur.
    
    list:
    Retourne la liste des commandes de l'utilisateur courant.
    
    retrieve:
    Retourne les détails d'une commande spécifique.
    
    create:
    Crée une nouvelle commande à partir du panier.
    
    Aucune opération de mise à jour ou de suppression n'est autorisée sur les commandes.
    """
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """
        Retourne différents serializers selon l'action.
        """
        if self.action == 'list':
            return OrderListSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        return OrderDetailSerializer
    
    def get_queryset(self):
        """
        Retourne les commandes selon le rôle de l'utilisateur.
        """
        user = self.request.user
        
        # Si l'utilisateur est un vendeur, retourner aussi les commandes contenant ses produits
        if hasattr(user, 'profile') and user.profile.is_vendor:
            # Obtenir les boutiques du vendeur
            vendor_stores = user.stores.all()
            
            # Retourner les commandes du client ET les commandes contenant des produits du vendeur
            return Order.objects.filter(
                Q(customer=user) | Q(items__store__in=vendor_stores)
            ).distinct()
        
        # Pour les clients normaux, retourner uniquement leurs commandes
        return Order.objects.filter(customer=user)
    
    def get_permissions(self):
        """
        Définir les permissions en fonction de l'action.
        """
        if self.action == 'retrieve':
            permission_classes = [permissions.IsAuthenticated, IsOrderOwnerOrVendor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

class VendorOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour la gestion des commandes par les vendeurs.
    
    list:
    Retourne la liste des commandes contenant des produits du vendeur.
    
    retrieve:
    Retourne les détails d'une commande spécifique.
    
    update_status:
    Met à jour le statut d'une commande (uniquement pour les commandes contenant des produits du vendeur).
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendor]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Retourne uniquement les commandes contenant des produits des boutiques du vendeur.
        """
        user = self.request.user
        
        # Obtenir les boutiques du vendeur
        vendor_stores = user.stores.all()
        
        # Retourner les commandes contenant des produits du vendeur
        return Order.objects.filter(
            items__store__in=vendor_stores
        ).distinct()
    
    @action(detail=True, methods=['put'])
    def update_status(self, request, pk=None):
        """
        Met à jour le statut d'une commande.
        """
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderDetailSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)