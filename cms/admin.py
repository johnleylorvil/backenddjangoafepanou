from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.db import models

from .models import Category, Tag, Author, Article, Page

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'article_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = _("Nombre d'articles")
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description')
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'article_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = _("Nombre d'articles")

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'article_count', 'display_avatar')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'bio')
    raw_id_fields = ('user',)
    
    def display_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    display_name.short_description = _("Nom")
    
    def article_count(self, obj):
        return obj.articles.count()
    article_count.short_description = _("Nombre d'articles")
    
    def display_avatar(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.avatar.url)
        return "-"
    display_avatar.short_description = _("Avatar")
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        (_('Profil'), {
            'fields': ('bio', 'avatar', 'website')
        }),
    )

class ArticleTagsInline(admin.TabularInline):
    model = Article.tags.through
    extra = 1
    verbose_name = _("Tag")
    verbose_name_plural = _("Tags")

class ArticleCategoriesInline(admin.TabularInline):
    model = Article.categories.through
    extra = 1
    verbose_name = _("Catégorie")
    verbose_name_plural = _("Catégories")

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'display_categories', 'display_featured_image', 'published_at', 'created_at')
    list_filter = ('status', 'categories', 'tags', 'author', 'created_at', 'published_at')
    search_fields = ('title', 'content', 'author__user__username', 'author__user__first_name', 'author__user__last_name')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'article_preview')
    date_hierarchy = 'published_at'
    save_on_top = True
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'author', 'status')
        }),
        (_('Contenu'), {
            'fields': ('content', 'featured_image', 'article_preview')
        }),
        (_('Catégorisation'), {
            'fields': ('categories', 'tags')
        }),
        (_('Publication'), {
            'fields': ('published_at',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    filter_horizontal = ('categories', 'tags')
    
    def display_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()[:3]])
    display_categories.short_description = _("Catégories")
    
    def display_featured_image(self, obj):
        if obj.featured_image:
            return format_html('<img src="{}" width="80" height="45" style="object-fit: cover;" />', obj.featured_image.url)
        return "-"
    display_featured_image.short_description = _("Image")
    
    def article_preview(self, obj):
        if obj.id:
            return format_html(
                '<a href="{}" class="button" target="_blank">{}</a>',
                reverse('admin:cms_article_preview', args=[obj.id]),
                _("Aperçu de l'article")
            )
        return _("Enregistrez l'article pour voir l'aperçu")
    article_preview.short_description = _("Aperçu")
    
    def save_model(self, request, obj, form, change):
        if obj.status == 'published' and not obj.published_at:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:article_id>/preview/',
                self.admin_site.admin_view(self.article_preview_view),
                name='cms_article_preview'
            ),
        ]
        return custom_urls + urls
    
    def article_preview_view(self, request, article_id):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        article = self.get_object(request, article_id)
        context = {
            'article': article,
            'is_preview': True,
        }
        content = render_to_string('cms/article_preview.html', context)
        return HttpResponse(content)
    
    actions = ['make_published', 'make_draft']
    
    def make_published(self, request, queryset):
        updated = queryset.filter(status='draft').update(status='published', published_at=timezone.now())
        self.message_user(request, _(f"{updated} article(s) ont été publiés."))
    make_published.short_description = _("Publier les articles sélectionnés")
    
    def make_draft(self, request, queryset):
        updated = queryset.filter(status='published').update(status='draft')
        self.message_user(request, _(f"{updated} article(s) ont été mis en brouillon."))
    make_draft.short_description = _("Mettre en brouillon les articles sélectionnés")

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'page_preview')
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'is_active')
        }),
        (_('Contenu'), {
            'fields': ('content', 'page_preview')
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def page_preview(self, obj):
        if obj.id:
            return format_html(
                '<a href="{}" class="button" target="_blank">{}</a>',
                reverse('admin:cms_page_preview', args=[obj.id]),
                _("Aperçu de la page")
            )
        return _("Enregistrez la page pour voir l'aperçu")
    page_preview.short_description = _("Aperçu")
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:page_id>/preview/',
                self.admin_site.admin_view(self.page_preview_view),
                name='cms_page_preview'
            ),
        ]
        return custom_urls + urls
    
    def page_preview_view(self, request, page_id):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        page = self.get_object(request, page_id)
        context = {
            'page': page,
            'is_preview': True,
        }
        content = render_to_string('cms/page_preview.html', context)
        return HttpResponse(content)
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, _(f"{updated} page(s) ont été activées."))
    make_active.short_description = _("Activer les pages sélectionnées")
    
    def make_inactive(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, _(f"{updated} page(s) ont été désactivées."))
    make_inactive.short_description = _("Désactiver les pages sélectionnées")


# Remarque: Vous devez créer les templates suivants dans le répertoire templates/cms/
# - article_preview.html
# - page_preview.html