# core/views.py

from rest_framework import status, viewsets, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer, 
    PasswordChangeSerializer, PasswordResetSerializer, UserUpdateSerializer
)
from .models import UserProfile

class RegisterView(generics.CreateAPIView):
    """
    Inscription d'un nouvel utilisateur.
    
    Crée un nouvel utilisateur avec les informations fournies.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "message": _("Inscription réussie")
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    """
    Connexion utilisateur.
    
    Authentifie l'utilisateur et renvoie les tokens JWT.
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = LoginSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if user is None:
            return Response({
                "error": _("Authentification échouée"),
                "message": _("Nom d'utilisateur ou mot de passe incorrect")
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Générer les tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": UserSerializer(user).data,
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "message": _("Connexion réussie")
        })

class LogoutView(APIView):
    """
    Déconnexion utilisateur.
    
    Ajoute le token de rafraîchissement à la liste noire.
    """
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": _("Le token de rafraîchissement est requis")},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": _("Déconnexion réussie")},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": _("Impossible de se déconnecter"), "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class UserProfileView(APIView):
    """
    Profil de l'utilisateur connecté.
    
    Permet de consulter et mettre à jour son profil.
    """
    def get(self, request, *args, **kwargs):
        """Obtenir les informations du profil de l'utilisateur connecté"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request, *args, **kwargs):
        """Mettre à jour les informations du profil de l'utilisateur connecté"""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            "user": UserSerializer(user).data,
            "message": _("Profil mis à jour avec succès")
        })

class PasswordChangeView(APIView):
    """
    Changement de mot de passe.
    
    Permet à l'utilisateur connecté de changer son mot de passe.
    """
    def post(self, request, *args, **kwargs):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Vérifier l'ancien mot de passe
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({
                "error": _("Mot de passe incorrect"),
                "message": _("L'ancien mot de passe est incorrect")
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mettre à jour le mot de passe
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            "message": _("Mot de passe modifié avec succès")
        })

class PasswordResetView(APIView):
    """
    Réinitialisation de mot de passe.
    
    Envoie un email avec un lien de réinitialisation du mot de passe.
    """
    permission_classes = (permissions.AllowAny,)
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            # Ici, vous devriez implémenter l'envoi d'un email avec un lien de réinitialisation
            # Pour l'exemple, nous allons simplement retourner un message de succès
            
            return Response({
                "message": _("Un email a été envoyé avec les instructions pour réinitialiser votre mot de passe")
            })
        except User.DoesNotExist:
            # Pour des raisons de sécurité, nous ne révélons pas si l'email existe ou non
            return Response({
                "message": _("Un email a été envoyé avec les instructions pour réinitialiser votre mot de passe")
            })