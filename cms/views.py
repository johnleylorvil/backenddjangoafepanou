# cms/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .models import Page, Article, Category, Tag, Author
from .serializers import (
    PageSerializer, ArticleListSerializer, ArticleDetailSerializer, 
    CategorySerializer, TagSerializer, AuthorSerializer
)
from .permissions import IsAdminOrReadOnly
from .filters import ArticleFilter

# CMS Views
class PageViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des pages CMS.
    
    list:
    Retourne la liste de toutes les pages actives.
    
    retrieve:
    Retourne les détails d'une page spécifique par slug.
    
    create:
    Crée une nouvelle page (admin seulement).
    
    update:
    Met à jour une page existante (admin seulement).
    
    destroy:
    Supprime une page (admin seulement).
    """
    queryset = Page.objects.all()
    serializer_class = PageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['title', 'created_at', 'updated_at']
    lookup_field = 'slug'
    
    def get_queryset(self):
        """
        Filtre les pages pour les utilisateurs non-admin.
        """
        queryset = Page.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        return queryset
    
    @action(detail=False, methods=['get'], url_path='by-slug/(?P<slug>[-\w]+)')
    def by_slug(self, request, slug=None):
        """
        Récupère une page par son slug.
        """
        page = get_object_or_404(self.get_queryset(), slug=slug)
        serializer = self.get_serializer(page)
        return Response(serializer.data)

# Blog Views
class CategoryViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des catégories d'articles.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    
    # Restreindre les actions disponibles
    http_method_names = ['get', 'post', 'put', 'delete']

class TagViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des tags d'articles.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    
    # Restreindre les actions disponibles
    http_method_names = ['get', 'post', 'put', 'delete']

class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour la consultation des auteurs d'articles.
    """
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]
    
    # Restreindre les actions disponibles (lecture seule)
    http_method_names = ['get']

class ArticleViewSet(viewsets.ModelViewSet):
    """
    API pour la gestion des articles de blog.
    
    list:
    Retourne la liste des articles publiés (avec pagination et filtres).
    
    retrieve:
    Retourne les détails d'un article spécifique par slug.
    
    create:
    Crée un nouvel article (admin seulement).
    
    update:
    Met à jour un article existant (admin seulement).
    
    destroy:
    Supprime un article (admin seulement).
    """
    queryset = Article.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ArticleFilter
    search_fields = ['title', 'content']
    ordering_fields = ['title', 'published_at', 'created_at']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        """
        Retourne différents serializers selon l'action.
        """
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer
    
    def get_queryset(self):
        """
        Filtre les articles pour les utilisateurs non-admin.
        """
        queryset = Article.objects.all().select_related('author', 'author__user').prefetch_related('categories', 'tags')
        if not self.request.user.is_staff:
            queryset = queryset.filter(status='published')
        return queryset
    
    @action(detail=False, methods=['get'], url_path='by-slug/(?P<slug>[-\w]+)')
    def by_slug(self, request, slug=None):
        """
        Récupère un article par son slug.
        """
        article = get_object_or_404(self.get_queryset(), slug=slug)
        serializer = ArticleDetailSerializer(article)
        return Response(serializer.data)