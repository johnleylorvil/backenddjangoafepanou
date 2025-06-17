# cms/permissions.py
from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée pour permettre uniquement aux administrateurs
    de créer, mettre à jour ou supprimer des objets. La lecture est autorisée pour tous.
    """
    def has_permission(self, request, view):
        # Autoriser les requêtes en lecture pour tous
        if request.method in permissions.SAFE_METHODS:
            return True
        # Autoriser les requêtes en écriture uniquement pour les administrateurs
        return request.user and request.user.is_staff