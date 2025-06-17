from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import Coalesce
from django.urls import reverse, path
from django.http import HttpResponse
from django.utils import timezone
import csv
import json
from datetime import timedelta

from .models import (
    Store, ProductCategory, ProductTag, Product, ProductImage,
    Address, Order, OrderItem
)

# Inlines
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'is_main', 'caption', 'preview_image')
    readonly_fields = ('preview_image',)
    
    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "-"
    preview_image.short_description = _("Aperçu")

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'subtotal')
    readonly_fields = ('subtotal',)
    
    def subtotal(self, obj):
        if obj.pk:
            return f"{obj.price * obj.quantity} {obj.product.get_currency_display()}"
        return "-"
    subtotal.short_description = _("Sous-total")

# Filters personnalisés
class ProductTypeFilter(admin.SimpleListFilter):
    title = _("Type de produit")
    parameter_name = 'product_type'
    
    def lookups(self, request, model_admin):
        return Product.PRODUCT_TYPE_CHOICES
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(product_type=self.value())
        return queryset

class StoreFilter(admin.SimpleListFilter):
    title = _("Boutique")
    parameter_name = 'store'
    
    def lookups(self, request, model_admin):
        return [(store.id, store.name) for store in Store.objects.all()]
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(store_id=self.value())
        return queryset

class PriceRangeFilter(admin.SimpleListFilter):
    title = _("Gamme de prix")
    parameter_name = 'price_range'
    
    def lookups(self, request, model_admin):
        return [
            ('low', _('Bas (< 1000 HTG)')),
            ('medium', _('Moyen (1000-5000 HTG)')),
            ('high', _('Élevé (> 5000 HTG)')),
        ]
    
    def queryset(self, request, queryset):
        if self.value() == 'low':
            return queryset.filter(price__lt=1000)
        if self.value() == 'medium':
            return queryset.filter(price__gte=1000, price__lte=5000)
        if self.value() == 'high':
            return queryset.filter(price__gt=5000)
        return queryset

# Modèles d'administration
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'product_count', 'active_status', 'display_logo', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'owner__username', 'owner__first_name', 'owner__last_name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'display_banner', 'display_logo', 'store_preview')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'owner', 'is_active')
        }),
        (_('Contenu'), {
            'fields': ('description',)
        }),
        (_('Images'), {
            'fields': ('logo', 'display_logo', 'banner', 'display_banner')
        }),
        (_('Prévisualisation'), {
            'fields': ('store_preview',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def active_status(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #2ecc71;">●</span> <span>Actif</span>')
        return format_html('<span style="color: #e74c3c;">●</span> <span>Inactif</span>')
    active_status.short_description = _("Statut")
    
    def product_count(self, obj):
        count = obj.products.count()
        if count > 0:
            return format_html(
                '<a href="{}?store__id__exact={}">{}</a>',
                reverse('admin:marketplace_product_changelist'),
                obj.id,
                count
            )
        return count
    product_count.short_description = _("Produits")
    
    def display_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.logo.url)
        return "-"
    display_logo.short_description = _("Aperçu du logo")
    
    def display_banner(self, obj):
        if obj.banner:
            return format_html('<img src="{}" style="max-height: 150px; max-width: 400px;" />', obj.banner.url)
        return "-"
    display_banner.short_description = _("Aperçu de la bannière")
    
    def store_preview(self, obj):
        if obj.id:
            return format_html(
                '<a href="{}" class="button" target="_blank">{}</a>',
                reverse('admin:marketplace_store_preview', args=[obj.id]),
                _("Aperçu de la boutique")
            )
        return _("Enregistrez la boutique pour voir l'aperçu")
    store_preview.short_description = _("Aperçu")
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(product_count=Count('products'))
        return queryset
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:store_id>/preview/',
                self.admin_site.admin_view(self.store_preview_view),
                name='marketplace_store_preview'
            ),
        ]
        return custom_urls + urls
    
    def store_preview_view(self, request, store_id):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        store = self.get_object(request, store_id)
        products = store.products.all()[:10]  # Limiter à 10 produits pour la prévisualisation
        
        context = {
            'store': store,
            'products': products,
            'is_preview': True,
        }
        
        content = render_to_string('marketplace/store_preview.html', context)
        return HttpResponse(content)
    
    actions = ['make_active', 'make_inactive']
    
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, _(f"{updated} boutique(s) ont été activées."))
    make_active.short_description = _("Activer les boutiques sélectionnées")
    
    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, _(f"{updated} boutique(s) ont été désactivées."))
    make_inactive.short_description = _("Désactiver les boutiques sélectionnées")

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'product_count', 'slug')
    list_filter = ('parent',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        count = obj.products.count()
        if count > 0:
            return format_html(
                '<a href="{}?categories__id__exact={}">{}</a>',
                reverse('admin:marketplace_product_changelist'),
                obj.id,
                count
            )
        return count
    product_count.short_description = _("Produits")
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(product_count=Count('products'))
        return queryset

@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        count = obj.products.count()
        if count > 0:
            return format_html(
                '<a href="{}?tags__id__exact={}">{}</a>',
                reverse('admin:marketplace_product_changelist'),
                obj.id,
                count
            )
        return count
    product_count.short_description = _("Produits")
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(product_count=Count('products'))
        return queryset

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'store', 'product_type_badge', 'price_display', 'status_badge', 'main_image_preview', 'created_at')
    list_filter = (ProductTypeFilter, StoreFilter, 'status', PriceRangeFilter, 'categories', 'tags', 'created_at')
    search_fields = ('name', 'description', 'store__name')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at', 'product_preview')
    filter_horizontal = ('categories', 'tags')
    date_hierarchy = 'created_at'
    inlines = [ProductImageInline]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'store', 'product_type', 'status')
        }),
        (_('Informations de prix'), {
            'fields': ('price', 'currency')
        }),
        (_('Détails'), {
            'fields': ('description',)
        }),
        (_('Catégorisation'), {
            'fields': ('categories', 'tags')
        }),
        (_('Attributs spécifiques'), {
            'fields': ('stock_quantity', 'duration', 'format'),
            'classes': ('wide',),
        }),
        (_('Prévisualisation'), {
            'fields': ('product_preview',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def product_type_badge(self, obj):
        type_colors = {
            'physical': '#3498db',
            'service': '#2ecc71',
            'training': '#f39c12'
        }
        color = type_colors.get(obj.product_type, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color,
            obj.get_product_type_display()
        )
    product_type_badge.short_description = _("Type")
    
    def price_display(self, obj):
        return f"{obj.price} {obj.get_currency_display()}"
    price_display.short_description = _("Prix")
    
    def status_badge(self, obj):
        status_colors = {
            'available': '#2ecc71',
            'out_of_stock': '#e74c3c',
            'discontinued': '#95a5a6'
        }
        color = status_colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _("Statut")
    
    def main_image_preview(self, obj):
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', main_image.image.url)
        
        # Si pas d'image principale, prendre la première
        first_image = obj.images.first()
        if first_image:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 50px;" />', first_image.image.url)
        
        return "-"
    main_image_preview.short_description = _("Image")
    
    def product_preview(self, obj):
        if obj.id:
            return format_html(
                '<a href="{}" class="button" target="_blank">{}</a>',
                reverse('admin:marketplace_product_preview', args=[obj.id]),
                _("Aperçu du produit")
            )
        return _("Enregistrez le produit pour voir l'aperçu")
    product_preview.short_description = _("Aperçu")
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:product_id>/preview/',
                self.admin_site.admin_view(self.product_preview_view),
                name='marketplace_product_preview'
            ),
        ]
        return custom_urls + urls
    
    def product_preview_view(self, request, product_id):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        product = self.get_object(request, product_id)
        context = {
            'product': product,
            'is_preview': True,
        }
        content = render_to_string('marketplace/product_preview.html', context)
        return HttpResponse(content)
    
    actions = ['make_available', 'mark_out_of_stock', 'mark_discontinued', 'export_products_csv']
    
    def make_available(self, request, queryset):
        updated = queryset.update(status='available')
        self.message_user(request, _(f"{updated} produit(s) ont été marqués comme disponibles."))
    make_available.short_description = _("Marquer comme disponible")
    
    def mark_out_of_stock(self, request, queryset):
        updated = queryset.update(status='out_of_stock')
        self.message_user(request, _(f"{updated} produit(s) ont été marqués en rupture de stock."))
    mark_out_of_stock.short_description = _("Marquer en rupture de stock")
    
    def mark_discontinued(self, request, queryset):
        updated = queryset.update(status='discontinued')
        self.message_user(request, _(f"{updated} produit(s) ont été marqués comme discontinués."))
    mark_discontinued.short_description = _("Marquer comme discontinué")
    
    def export_products_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="products.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nom', 'Boutique', 'Type', 'Prix', 'Devise', 'Statut', 
            'Stock', 'Durée', 'Format', 'Date de création'
        ])
        
        for product in queryset:
            writer.writerow([
                product.id,
                product.name,
                product.store.name,
                product.get_product_type_display(),
                product.price,
                product.get_currency_display(),
                product.get_status_display(),
                product.stock_quantity or '',
                product.duration or '',
                product.format or '',
                product.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_products_csv.short_description = _("Exporter les produits sélectionnés en CSV")

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview', 'is_main', 'caption')
    list_filter = ('is_main', 'product__store')
    search_fields = ('product__name', 'caption')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 100px;" />', obj.image.url)
        return "-"
    image_preview.short_description = _("Aperçu")
    
    actions = ['make_main_image', 'make_not_main_image']
    
    def make_main_image(self, request, queryset):
        # D'abord, pour chaque produit concerné, on remet toutes ses images à non-principales
        for product_id in queryset.values_list('product_id', flat=True).distinct():
            ProductImage.objects.filter(product_id=product_id).update(is_main=False)
        
        # Ensuite, on marque les images sélectionnées comme principales
        updated = queryset.update(is_main=True)
        self.message_user(request, _(f"{updated} image(s) ont été définies comme principales."))
    make_main_image.short_description = _("Définir comme image principale")
    
    def make_not_main_image(self, request, queryset):
        updated = queryset.update(is_main=False)
        self.message_user(request, _(f"{updated} image(s) ont été définies comme non principales."))
    make_not_main_image.short_description = _("Définir comme image secondaire")

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'city', 'state', 'phone', 'is_default')
    list_filter = ('is_default', 'city', 'state')
    search_fields = ('name', 'user__username', 'address_line1', 'address_line2', 'city', 'phone')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'is_default')
        }),
        (_('Adresse'), {
            'fields': ('address_line1', 'address_line2', 'city', 'state')
        }),
        (_('Contact'), {
            'fields': ('phone',)
        }),
    )
    
    actions = ['make_default', 'make_not_default']
    
    def make_default(self, request, queryset):
        # Pour chaque utilisateur concerné, on remet toutes ses adresses à non par défaut
        for user_id in queryset.values_list('user_id', flat=True).distinct():
            Address.objects.filter(user_id=user_id).update(is_default=False)
        
        # Ensuite, on marque les adresses sélectionnées comme par défaut
        updated = queryset.update(is_default=True)
        self.message_user(request, _(f"{updated} adresse(s) ont été définies comme par défaut."))
    make_default.short_description = _("Définir comme adresse par défaut")
    
    def make_not_default(self, request, queryset):
        updated = queryset.update(is_default=False)
        self.message_user(request, _(f"{updated} adresse(s) ont été définies comme non par défaut."))
    make_not_default.short_description = _("Définir comme adresse secondaire")

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'customer', 'status_badge', 'total_amount_display', 'item_count', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'customer__username', 'customer__first_name', 'customer__last_name', 'shipping_address__address_line1', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'order_summary', 'payment_status')
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    
    fieldsets = (
        (None, {
            'fields': ('order_number', 'customer', 'status')
        }),
        (_('Livraison'), {
            'fields': ('shipping_address', 'shipping_cost')
        }),
        (_('Détails financiers'), {
            'fields': ('total_amount', 'payment_status')
        }),
        (_('Résumé de la commande'), {
            'fields': ('order_summary',)
        }),
        (_('Notes'), {
            'fields': ('notes',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def status_badge(self, obj):
        status_colors = {
            'pending': '#f39c12',
            'paid': '#3498db',
            'processing': '#9b59b6',
            'shipped': '#2ecc71',
            'delivered': '#27ae60',
            'cancelled': '#e74c3c'
        }
        color = status_colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _("Statut")
    
    def total_amount_display(self, obj):
        return f"{obj.total_amount} HTG"
    total_amount_display.short_description = _("Montant total")
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = _("Articles")
    
    def payment_status(self, obj):
        from payments.models import PaymentTransaction
        
        try:
            payment = PaymentTransaction.objects.filter(order=obj).latest('created_at')
            if payment.status == 'success':
                return format_html('<span style="color: #2ecc71; font-weight: bold;">✓ Payé</span>')
            elif payment.status == 'pending':
                return format_html('<span style="color: #f39c12; font-weight: bold;">⏳ En attente</span>')
            elif payment.status == 'failed':
                return format_html('<span style="color: #e74c3c; font-weight: bold;">✗ Échec</span>')
            else:
                return format_html('<span style="color: #95a5a6; font-weight: bold;">? Statut inconnu</span>')
        except:
            return format_html('<span style="color: #95a5a6; font-weight: bold;">Pas de paiement</span>')
    payment_status.short_description = _("Statut du paiement")
    
    def order_summary(self, obj):
        if not obj.pk:
            return _("Disponible après enregistrement")
        
        items = obj.items.all()
        
        html = """
        <div style="margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">Résumé de la commande</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #eee;">
                        <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Produit</th>
                        <th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">Quantité</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">Prix unitaire</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">Sous-total</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for item in items:
            html += f"""
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{item.product.name}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: center;">{item.quantity}</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{item.price} HTG</td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">{item.price * item.quantity} HTG</td>
                </tr>
            """
        
        html += f"""
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="3" style="padding: 8px; text-align: right;"><strong>Sous-total:</strong></td>
                        <td style="padding: 8px; text-align: right;">{obj.total_amount - obj.shipping_cost} HTG</td>
                    </tr>
                    <tr>
                        <td colspan="3" style="padding: 8px; text-align: right;"><strong>Frais de livraison:</strong></td>
                        <td style="padding: 8px; text-align: right;">{obj.shipping_cost} HTG</td>
                    </tr>
                    <tr>
                        <td colspan="3" style="padding: 8px; text-align: right;"><strong>Total:</strong></td>
                        <td style="padding: 8px; text-align: right; font-weight: bold;">{obj.total_amount} HTG</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """
        
        return format_html(html)
    order_summary.short_description = _("Résumé de la commande")
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(item_count=Count('items'))
        return queryset
    
    actions = [
        'mark_as_paid', 'mark_as_processing', 'mark_as_shipped', 
        'mark_as_delivered', 'mark_as_cancelled', 'export_orders_csv'
    ]
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='paid')
        self.message_user(request, _(f"{updated} commande(s) ont été marquées comme payées."))
    mark_as_paid.short_description = _("Marquer comme payées")
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.filter(status='paid').update(status='processing')
        self.message_user(request, _(f"{updated} commande(s) ont été marquées comme en traitement."))
    mark_as_processing.short_description = _("Marquer comme en traitement")
    
    def mark_as_shipped(self, request, queryset):
        updated = queryset.filter(status='processing').update(status='shipped')
        self.message_user(request, _(f"{updated} commande(s) ont été marquées comme expédiées."))
    mark_as_shipped.short_description = _("Marquer comme expédiées")
    
    def mark_as_delivered(self, request, queryset):
        updated = queryset.filter(status='shipped').update(status='delivered')
        self.message_user(request, _(f"{updated} commande(s) ont été marquées comme livrées."))
    mark_as_delivered.short_description = _("Marquer comme livrées")
    
    def mark_as_cancelled(self, request, queryset):
        updated = queryset.exclude(status__in=['delivered', 'cancelled']).update(status='cancelled')
        self.message_user(request, _(f"{updated} commande(s) ont été marquées comme annulées."))
    mark_as_cancelled.short_description = _("Marquer comme annulées")
    
    def export_orders_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Numéro de commande', 'Client', 'Date', 'Statut', 
            'Montant total', 'Frais de livraison', 'Adresse de livraison'
        ])
        
        for order in queryset:
            shipping_address = f"{order.shipping_address.address_line1}, {order.shipping_address.city}" if order.shipping_address else "-"
            writer.writerow([
                order.order_number,
                order.customer.get_full_name() or order.customer.username,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.get_status_display(),
                order.total_amount,
                order.shipping_cost,
                shipping_address
            ])
        
        return response
    export_orders_csv.short_description = _("Exporter les commandes sélectionnées en CSV")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'order_number', 'quantity', 'price', 'subtotal')
    list_filter = ('order__status', 'product__store')
    search_fields = ('product__name', 'order__order_number')
    
    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = _("Produit")
    product_name.admin_order_field = 'product__name'
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = _("Commande")
    order_number.admin_order_field = 'order__order_number'
    
    def subtotal(self, obj):
        return f"{obj.price * obj.quantity} HTG"
    subtotal.short_description = _("Sous-total")

# Templates nécessaires
# templates/marketplace/store_preview.html
# templates/marketplace/product_preview.html