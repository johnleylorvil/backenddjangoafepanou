# blog/filters.py
from django_filters import rest_framework as filters
from .models import Article, Category, Tag

class ArticleFilter(filters.FilterSet):
    """
    Filtres pour les articles de blog.
    """
    title = filters.CharFilter(field_name='title', lookup_expr='icontains')
    category = filters.ModelMultipleChoiceFilter(
        field_name='categories__slug',
        to_field_name='slug',
        queryset=Category.objects.all()
    )
    tag = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    author = filters.CharFilter(field_name='author__user__username')
    status = filters.ChoiceFilter(field_name='status', choices=Article.STATUS_CHOICES)
    created_after = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Article
        fields = ['title', 'category', 'tag', 'author', 'status', 'created_after', 'created_before']