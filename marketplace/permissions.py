# marketplace/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée pour permettre uniquement aux propriétaires
    de modifier ou supprimer leurs objets. La lecture est autorisée pour tous.
    """
    def has_object_permission(self, request, view, obj):
        # Autorise les méthodes GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Vérifie si l'objet a un attribut 'owner'
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        # Pour les autres types d'objets (par exemple CartItem)
        if hasattr(obj, 'cart') and hasattr(obj.cart, 'user'):
            return obj.cart.user == request.user
        
        return False

class IsVendor(permissions.BasePermission):
    """
    Permission pour les actions réservées aux vendeurs.
    """
    def has_permission(self, request, view):
        # Vérifie si l'utilisateur a un profil avec is_vendor=True
        return request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.is_vendor

class IsStoreOwner(permissions.BasePermission):
    """
    Permission pour vérifier si l'utilisateur est propriétaire de la boutique.
    """
    def has_object_permission(self, request, view, obj):
        # Pour les produits, vérifier le propriétaire de la boutique
        if hasattr(obj, 'store'):
            return obj.store.owner == request.user
        
        # Pour les boutiques
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False

class IsOrderOwnerOrVendor(permissions.BasePermission):
    """
    Permission pour les commandes: le client peut voir ses commandes,
    le vendeur peut voir les commandes qui contiennent ses produits.
    """
    def has_object_permission(self, request, view, obj):
        # Le client peut voir sa propre commande
        if obj.customer == request.user:
            return True
        
        # Un vendeur peut voir les commandes qui contiennent ses produits
        if hasattr(request.user, 'profile') and request.user.profile.is_vendor:
            # Vérifie si la commande contient des produits de ce vendeur
            vendor_stores = request.user.stores.all()
            return obj.items.filter(store__in=vendor_stores).exists()
        
        return False