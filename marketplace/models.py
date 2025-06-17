from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel
from ckeditor.fields import RichTextField

class Store(TimeStampedModel):
    """
    Boutiques des vendeurs.
    """
    name = models.CharField(_("Nom"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=120, unique=True)
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='stores',
        verbose_name=_("Propriétaire")
    )
    description = RichTextField(_("Description"))
    logo = models.ImageField(_("Logo"), upload_to='stores/logos/')
    banner = models.ImageField(_("Bannière"), upload_to='stores/banners/', blank=True)
    is_active = models.BooleanField(_("Actif"), default=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Boutique")
        verbose_name_plural = _("Boutiques")

class ProductCategory(models.Model):
    """
    Catégories de produits.
    """
    name = models.CharField(_("Nom"), max_length=100)
    slug = models.SlugField(_("Slug"), max_length=120, unique=True)
    description = models.TextField(_("Description"), blank=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='children',
        verbose_name=_("Catégorie parente")
    )
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Catégorie de produit")
        verbose_name_plural = _("Catégories de produits")

class ProductTag(models.Model):
    """
    Tags pour les produits.
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
        verbose_name = _("Tag de produit")
        verbose_name_plural = _("Tags de produits")

class Product(TimeStampedModel):
    """
    Produits et services.
    """
    PRODUCT_TYPE_CHOICES = (
        ('physical', _('Produit physique')),
        ('service', _('Service')),
        ('training', _('Formation')),
    )
    
    STATUS_CHOICES = (
        ('available', _('Disponible')),
        ('out_of_stock', _('Rupture de stock')),
        ('discontinued', _('Discontinué')),
    )
    
    CURRENCY_CHOICES = (
        ('HTG', _('Gourde haïtienne')),
        ('USD', _('Dollar américain')),
    )
    
    name = models.CharField(_("Nom"), max_length=200)
    slug = models.SlugField(_("Slug"), max_length=220, unique=True)
    store = models.ForeignKey(
        Store, 
        on_delete=models.CASCADE, 
        related_name='products',
        verbose_name=_("Boutique")
    )
    product_type = models.CharField(
        _("Type de produit"), 
        max_length=10, 
        choices=PRODUCT_TYPE_CHOICES
    )
    description = RichTextField(_("Description"))
    price = models.DecimalField(_("Prix"), max_digits=10, decimal_places=2)
    currency = models.CharField(
        _("Devise"), 
        max_length=3, 
        choices=CURRENCY_CHOICES, 
        default='HTG'
    )
    status = models.CharField(
        _("Statut"), 
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='available'
    )
    categories = models.ManyToManyField(
        ProductCategory, 
        related_name='products',
        verbose_name=_("Catégories")
    )
    tags = models.ManyToManyField(
        ProductTag, 
        related_name='products',
        verbose_name=_("Tags")
    )
    
    # Champs spécifiques par type de produit
    stock_quantity = models.PositiveIntegerField(_("Quantité en stock"), null=True, blank=True)
    duration = models.CharField(_("Durée"), max_length=100, blank=True)
    format = models.CharField(_("Format"), max_length=100, blank=True)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = _("Produit")
        verbose_name_plural = _("Produits")

class ProductImage(models.Model):
    """
    Images de produits.
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='images',
        verbose_name=_("Produit")
    )
    image = models.ImageField(_("Image"), upload_to='products/')
    is_main = models.BooleanField(_("Image principale"), default=False)
    caption = models.CharField(_("Légende"), max_length=200, blank=True)
    
    def __str__(self):
        return f"Image de {self.product.name}"
    
    class Meta:
        verbose_name = _("Image de produit")
        verbose_name_plural = _("Images de produits")

class Address(models.Model):
    """
    Adresses des clients.
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='addresses',
        verbose_name=_("Utilisateur")
    )
    name = models.CharField(_("Nom complet"), max_length=100)
    address_line1 = models.CharField(_("Adresse ligne 1"), max_length=200)
    address_line2 = models.CharField(_("Adresse ligne 2"), max_length=200, blank=True)
    city = models.CharField(_("Ville"), max_length=100)
    state = models.CharField(_("Département"), max_length=100)
    phone = models.CharField(_("Téléphone"), max_length=30)
    is_default = models.BooleanField(_("Adresse par défaut"), default=False)
    
    def __str__(self):
        return f"{self.name} - {self.city}"
    
    class Meta:
        verbose_name = _("Adresse")
        verbose_name_plural = _("Adresses")

class Order(TimeStampedModel):
    """
    Commandes des clients.
    """
    STATUS_CHOICES = (
        ('pending', _('En attente')),
        ('paid', _('Payée')),
        ('processing', _('En traitement')),
        ('shipped', _('Expédiée')),
        ('delivered', _('Livrée')),
        ('cancelled', _('Annulée')),
    )
    
    customer = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='orders',
        verbose_name=_("Client")
    )
    order_number = models.CharField(_("Numéro de commande"), max_length=20, unique=True)
    status = models.CharField(
        _("Statut"), 
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    shipping_address = models.ForeignKey(
        Address, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='shipping_orders',
        verbose_name=_("Adresse de livraison")
    )
    total_amount = models.DecimalField(_("Montant total"), max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(_("Frais de livraison"), max_digits=8, decimal_places=2, default=0)
    notes = models.TextField(_("Notes"), blank=True)
    
    def __str__(self):
        return f"Commande #{self.order_number}"
    
    class Meta:
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")

class OrderItem(models.Model):
    """
    Articles d'une commande.
    """
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='items',
        verbose_name=_("Commande")
    )
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='order_items',
        verbose_name=_("Produit")
    )
    quantity = models.PositiveIntegerField(_("Quantité"))
    price = models.DecimalField(_("Prix unitaire"), max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} ({self.quantity}) - Commande #{self.order.order_number}"
    
    @property
    def subtotal(self):
        return self.price * self.quantity
    
    class Meta:
        verbose_name = _("Article de commande")
        verbose_name_plural = _("Articles de commande")