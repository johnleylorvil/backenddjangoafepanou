from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from ckeditor.fields import RichTextField
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel

class Category(TimeStampedModel):
    """
    Catégories pour les articles de blog.
    """
    name = models.CharField(_("Nom"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=120, unique=True)
    description = models.TextField(_("Description"), blank=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")

class Tag(models.Model):
    """
    Tags pour les articles de blog.
    """
    name = models.CharField(_("Nom"), max_length=50)
    slug = models.SlugField(_("Slug"), max_length=70, unique=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")

class Author(models.Model):
    """
    Profil d'auteur pour les articles de blog.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='author_profile',
        verbose_name=_("Utilisateur")
    )
    bio = models.TextField(_("Biographie"))
    avatar = models.ImageField(_("Avatar"), upload_to='authors/', blank=True)
    website = models.URLField(_("Site web"), blank=True)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    class Meta:
        verbose_name = _("Auteur")
        verbose_name_plural = _("Auteurs")

class Article(TimeStampedModel):
    """
    Articles de blog.
    """
    STATUS_CHOICES = (
        ('draft', _('Brouillon')),
        ('published', _('Publié')),
    )
    
    title = models.CharField(_("Titre"), max_length=200)
    slug = models.SlugField(_("Slug"), max_length=220, unique=True)
    author = models.ForeignKey(
        Author, 
        on_delete=models.CASCADE, 
        related_name='articles',
        verbose_name=_("Auteur")
    )
    content = RichTextField(_("Contenu"))
    featured_image = models.ImageField(_("Image à la une"), upload_to='blog/')
    categories = models.ManyToManyField(
        Category, 
        related_name='articles',
        verbose_name=_("Catégories")
    )
    tags = models.ManyToManyField(
        Tag, 
        related_name='articles',
        verbose_name=_("Tags")
    )
    status = models.CharField(
        _("Statut"), 
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='draft'
    )
    published_at = models.DateTimeField(_("Date de publication"), null=True, blank=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ['-published_at', '-created_at']

class Page(TimeStampedModel):
    """
    Pages du site (accueil, à propos, contact, etc.).
    """
    title = models.CharField(_("Titre"), max_length=200)
    slug = models.SlugField(_("Slug"), max_length=220, unique=True)
    content = RichTextField(_("Contenu"))
    is_active = models.BooleanField(_("Actif"), default=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")