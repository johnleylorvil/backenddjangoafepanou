# cms/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Page, Article, Category, Tag, Author

# Serializers de base
class UserBasicSerializer(serializers.ModelSerializer):
    """
    Serializer basique pour les utilisateurs.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

# CMS Serializers
class PageSerializer(serializers.ModelSerializer):
    """
    Serializer pour les pages CMS.
    """
    class Meta:
        model = Page
        fields = ['id', 'title', 'slug', 'content', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'slug': {'required': False}  # Le slug sera généré automatiquement si non fourni
        }

# Blog Serializers
class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories d'articles.
    """
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'slug': {'required': False}
        }

class TagSerializer(serializers.ModelSerializer):
    """
    Serializer pour les tags d'articles.
    """
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id']
        extra_kwargs = {
            'slug': {'required': False}
        }

class AuthorSerializer(serializers.ModelSerializer):
    """
    Serializer pour les auteurs d'articles.
    """
    user = UserBasicSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        source='user', 
        queryset=User.objects.all(),
        write_only=True
    )
    
    class Meta:
        model = Author
        fields = ['id', 'user', 'user_id', 'bio', 'avatar', 'website']
        read_only_fields = ['id']
    
    def create(self, validated_data):
        user = validated_data.pop('user')
        author = Author.objects.create(user=user, **validated_data)
        return author

class ArticleListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des articles (version allégée).
    """
    author = serializers.SerializerMethodField()
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'author', 'featured_image', 
            'categories', 'tags', 'status', 'published_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_author(self, obj):
        return {
            'id': obj.author.id,
            'name': obj.author.user.get_full_name() or obj.author.user.username
        }

class ArticleDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour le détail d'un article.
    """
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        source='author', 
        queryset=Author.objects.all(),
        write_only=True
    )
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        source='categories',
        queryset=Category.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'author', 'author_id', 'content', 'featured_image',
            'categories', 'category_ids', 'tags', 'tag_ids', 'status',
            'published_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'slug': {'required': False}
        }
    
    def create(self, validated_data):
        # Extraire les relations many-to-many
        categories = validated_data.pop('categories', [])
        tags = validated_data.pop('tags', [])
        
        # Créer l'article
        article = Article.objects.create(**validated_data)
        
        # Ajouter les relations many-to-many
        if categories:
            article.categories.set(categories)
        if tags:
            article.tags.set(tags)
        
        return article
    
    def update(self, instance, validated_data):
        # Extraire les relations many-to-many
        categories = validated_data.pop('categories', None)
        tags = validated_data.pop('tags', None)
        
        # Mettre à jour les champs simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Mettre à jour les relations many-to-many
        if categories is not None:
            instance.categories.set(categories)
        if tags is not None:
            instance.tags.set(tags)
        
        return instance