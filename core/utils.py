# core/utils.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework.exceptions import (
    AuthenticationFailed, NotAuthenticated, ValidationError, 
    APIException, ParseError, NotFound
)

def custom_exception_handler(exc, context):
    """
    Gestionnaire d'exceptions personnalisé pour standardiser les réponses d'erreur.
    """
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = AuthenticationFailed("Vous n'avez pas les permissions nécessaires pour effectuer cette action.")
    
    response = exception_handler(exc, context)
    
    # Si le gestionnaire d'exceptions par défaut n'a pas traité l'exception
    if response is None:
        if isinstance(exc, Exception):
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return None
    
    # Formatage standard des erreurs
    if isinstance(exc, ValidationError):
        return Response(
            {"error": "Données invalides", "details": response.data},
            status=status.HTTP_400_BAD_REQUEST
        )
    elif isinstance(exc, AuthenticationFailed):
        return Response(
            {"error": "Authentification échouée", "message": str(exc)},
            status=status.HTTP_401_UNAUTHORIZED
        )
    elif isinstance(exc, NotAuthenticated):
        return Response(
            {"error": "Authentification requise", "message": "Vous devez être connecté pour accéder à cette ressource"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    elif isinstance(exc, NotFound):
        return Response(
            {"error": "Ressource non trouvée", "message": "La ressource demandée n'existe pas"},
            status=status.HTTP_404_NOT_FOUND
        )
    elif isinstance(exc, ParseError):
        return Response(
            {"error": "Format de données invalide", "message": str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Pour les autres exceptions, on garde la réponse standard
    return response