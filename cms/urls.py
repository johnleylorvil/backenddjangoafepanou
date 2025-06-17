# cms/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PageViewSet, ArticleViewSet, CategoryViewSet, TagViewSet, AuthorViewSet

router = DefaultRouter()

# CMS routes
router.register(r'pages', PageViewSet, basename='page')

# Blog routes - nous les incluons ici car blog fait partie de l'app cms
router.register(r'blog/articles', ArticleViewSet, basename='article')
router.register(r'blog/categories', CategoryViewSet, basename='category')
router.register(r'blog/tags', TagViewSet, basename='tag')
router.register(r'blog/authors', AuthorViewSet, basename='author')

app_name = 'cms'

urlpatterns = [
    path('', include(router.urls)),
]