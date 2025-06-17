# core/serializers.py

from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile
from rest_framework.validators import UniqueValidator
from django.utils.translation import gettext_lazy as _

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('phone', 'address', 'date_of_birth', 'profile_image', 'is_vendor', 'created_at')
        read_only_fields = ('created_at', 'is_vendor')

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile')
        read_only_fields = ('id',)

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message=_("Un utilisateur avec cet email existe déjà"))]
    )
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 
                  'first_name', 'last_name', 'phone', 'address')
    
    def validate(self, attrs):
        """Validation personnalisée pour s'assurer que les mots de passe correspondent"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": _("Les mots de passe ne correspondent pas")})
        
        # Vérifier que l'email n'est pas déjà utilisé
        email = attrs.get('email', '').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": _("Un utilisateur avec cet email existe déjà")})
        
        return attrs
    
    def create(self, validated_data):
        """Création de l'utilisateur avec les données validées"""
        # Extraire les données du profil
        phone = validated_data.pop('phone', '')
        address = validated_data.pop('address', '')
        
        # Supprimer le champ password_confirm
        validated_data.pop('password_confirm')
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'].lower(),
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        
        # Mettre à jour le profil
        if phone or address:
            profile = user.profile
            if phone:
                profile.phone = phone
            if address:
                profile.address = address
            profile.save()
        
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    password = serializers.CharField(
        write_only=True, required=True,
        style={'input_type': 'password'}
    )

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True, required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        write_only=True, required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validation personnalisée pour s'assurer que les nouveaux mots de passe correspondent"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Les nouveaux mots de passe ne correspondent pas")}
            )
        return attrs

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour du profil utilisateur"""
    profile = UserProfileSerializer(required=False)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'profile')
    
    def update(self, instance, validated_data):
        """Met à jour l'utilisateur et son profil"""
        # Mettre à jour les champs de l'utilisateur
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        
        # Mettre à jour le profil s'il est fourni
        profile_data = validated_data.get('profile')
        if profile_data:
            profile = instance.profile
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance