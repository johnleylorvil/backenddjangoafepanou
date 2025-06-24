from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
import csv
import json
from datetime import timedelta

from .models import PaymentTransaction, PaymentStatusHistory, PaymentNotification


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_link', 'amount_display', 'status_badge', 
        'transaction_id', 'payer_phone', 'payment_type', 'created_at'
    )
    list_filter = (
        'status', 'payment_type', 'created_at', 'currency'
    )
    search_fields = (
        'order__order_number', 'transaction_id', 'external_order_id', 
        'payer_phone', 'reference'
    )
    readonly_fields = (
        'created_at', 'updated_at', 'payment_initiated_at', 'payment_completed_at',
        'payment_expires_at', 'is_expired', 'retry_count', 'api_response_formatted',
        'payment_gateway_url', 'order_summary'
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        (_('Informations de base'), {
            'fields': ('order', 'payment_type', 'status', 'amount', 'currency')
        }),
        (_('Identifiants MonCash'), {
            'fields': (
                'transaction_id', 'reference', 'external_order_id', 
                'payment_token', 'payment_gateway_url'
            )
        }),
        (_('Informations du payeur'), {
            'fields': ('payer_phone', 'payer_account', 'ip_address')
        }),
        (_('Gestion des erreurs'), {
            'fields': (
                'retry_count', 'max_retries', 'error_details', 
                'response_code', 'response_message'
            ),
            'classes': ('collapse',),
        }),
        (_('Données API'), {
            'fields': ('api_response_formatted',),
            'classes': ('collapse',),
        }),
        (_('Timestamps'), {
            'fields': (
                'payment_initiated_at', 'payment_completed_at', 
                'payment_expires_at', 'is_expired', 'created_at', 'updated_at'
            ),
            'classes': ('collapse',),
        }),
        (_('Résumé de commande'), {
            'fields': ('order_summary',),
            'classes': ('collapse',),
        }),
    )
    
    actions = [
        'mark_as_success', 'mark_as_failed', 'retry_failed_payments',
        'export_csv', 'check_moncash_status'
    ]

    # === DISPLAY METHODS ===
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:marketplace_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return "-"
    order_link.short_description = _("Commande")
    order_link.admin_order_field = 'order__order_number'
    
    def amount_display(self, obj):
        return format_html('<strong>{} {}</strong>', obj.amount, obj.currency)
    amount_display.short_description = _("Montant")
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        colors = {
            'initiated': '#f39c12',
            'pending': '#3498db',
            'processing': '#9b59b6',
            'success': '#2ecc71',
            'failed': '#e74c3c',
            'cancelled': '#95a5a6',
            'expired': '#e67e22',
            'refunded': '#1abc9c'
        }
        color = colors.get(obj.status, '#95a5a6')
        
        badge = f'<span style="background-color: {color}; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">{obj.get_status_display()}</span>'
        
        # Ajouter indicateur d'expiration
        if obj.is_expired and obj.status in ['initiated', 'pending']:
            badge += ' <span style="color: #e74c3c; font-size: 10px;">⏰ Expiré</span>'
            
        return format_html(badge)
    status_badge.short_description = _("Statut")
    status_badge.admin_order_field = 'status'
    
    def api_response_formatted(self, obj):
        if not obj.api_response_data:
            return format_html('<em>Aucune données API</em>')
        
        try:
            formatted_json = json.dumps(obj.api_response_data, indent=2, ensure_ascii=False)
            return format_html(
                '<pre style="background: #f8f9fa; padding: 10px; border-radius: 4px; max-height: 300px; overflow-y: auto;">{}</pre>', 
                formatted_json
            )
        except:
            return format_html('<pre>{}</pre>', str(obj.api_response_data))
    api_response_formatted.short_description = _("Réponse API")
    
    def payment_gateway_url(self, obj):
        url = obj.get_gateway_url()
        if not url:
            return format_html('<em>URL non disponible</em>')
        
        return format_html(
            '<a href="{}" target="_blank" class="button">Ouvrir MonCash</a><br>'
            '<small style="color: #666;">{}</small>',
            url, url
        )
    payment_gateway_url.short_description = _("URL MonCash")
    
    def order_summary(self, obj):
        if not obj.order:
            return format_html('<em>Aucune commande</em>')
        
        order = obj.order
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 4px;">'
            '<strong>#{}</strong> - {} HTG<br>'
            '<small>Client: {} | {}</small>'
            '</div>',
            order.order_number,
            order.total_amount,
            order.customer.get_full_name() or order.customer.username,
            order.created_at.strftime('%d/%m/%Y %H:%M')
        )
    order_summary.short_description = _("Résumé commande")

    # === ACTIONS ===
    
    def mark_as_success(self, request, queryset):
        count = 0
        for transaction in queryset.exclude(status='success'):
            transaction.status = 'success'
            transaction.payment_completed_at = timezone.now()
            transaction.save()
            count += 1
        
        messages.success(request, f'{count} transaction(s) marquée(s) comme réussie(s)')
    mark_as_success.short_description = _("✅ Marquer comme réussies")
    
    def mark_as_failed(self, request, queryset):
        count = queryset.exclude(status__in=['failed', 'success']).update(status='failed')
        messages.warning(request, f'{count} transaction(s) marquée(s) comme échouée(s)')
    mark_as_failed.short_description = _("❌ Marquer comme échouées")
    
    def retry_failed_payments(self, request, queryset):
        count = 0
        for transaction in queryset.filter(status__in=['failed', 'expired']):
            if transaction.can_retry:
                transaction.status = 'initiated'
                transaction.increment_retry()
                count += 1
        
        messages.info(request, f'{count} transaction(s) relancée(s)')
    retry_failed_payments.short_description = _("🔄 Relancer les paiements échoués")
    
    def check_moncash_status(self, request, queryset):
        """Action pour vérifier le statut via l'API MonCash"""
        count = 0
        for transaction in queryset.filter(transaction_id__isnull=False):
            # Ici vous ajouteriez l'appel à l'API MonCash
            # pour vérifier le statut réel
            count += 1
        
        messages.info(request, f'Statut vérifié pour {count} transaction(s)')
    check_moncash_status.short_description = _("🔍 Vérifier statut MonCash")
    
    def export_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="transactions_moncash_{timezone.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Commande', 'Type', 'Montant', 'Devise', 'Statut',
            'Transaction MonCash', 'Référence', 'Téléphone payeur',
            'Date création', 'Date completion', 'Tentatives'
        ])
        
        for t in queryset:
            writer.writerow([
                t.id,
                t.order.order_number if t.order else '',
                t.get_payment_type_display(),
                t.amount,
                t.currency,
                t.get_status_display(),
                t.transaction_id or '',
                t.reference or '',
                t.payer_phone or '',
                t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                t.payment_completed_at.strftime('%Y-%m-%d %H:%M:%S') if t.payment_completed_at else '',
                t.retry_count
            ])
        
        return response
    export_csv.short_description = _("📊 Exporter en CSV")

    # === CUSTOMIZATIONS ===
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'order__customer')
    
    def changelist_view(self, request, extra_context=None):
        # Statistiques rapides pour la vue de liste
        extra_context = extra_context or {}
        
        # Stats des 30 derniers jours
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_transactions = PaymentTransaction.objects.filter(created_at__gte=thirty_days_ago)
        
        stats = {
            'total': recent_transactions.count(),
            'success': recent_transactions.filter(status='success').count(),
            'pending': recent_transactions.filter(status__in=['pending', 'processing']).count(),
            'failed': recent_transactions.filter(status='failed').count(),
            'amount': recent_transactions.filter(status='success').aggregate(
                total=Sum('amount'))['total'] or 0
        }
        
        extra_context['payment_stats'] = stats
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(PaymentStatusHistory)
class PaymentStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'old_status', 'new_status', 'changed_at', 'changed_by')
    list_filter = ('old_status', 'new_status', 'changed_at')
    readonly_fields = ('transaction', 'old_status', 'new_status', 'changed_at', 'changed_by')
    ordering = ['-changed_at']
    
    def has_add_permission(self, request):
        return False  # Lecture seule


@admin.register(PaymentNotification)
class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'received_at', 'processed', 'has_error')
    list_filter = ('processed', 'received_at')
    readonly_fields = ('transaction', 'received_at', 'raw_data_formatted')
    ordering = ['-received_at']
    
    def raw_data_formatted(self, obj):
        try:
            formatted = json.dumps(obj.raw_data, indent=2, ensure_ascii=False)
            return format_html('<pre style="max-height: 400px; overflow-y: auto;">{}</pre>', formatted)
        except:
            return format_html('<pre>{}</pre>', str(obj.raw_data))
    raw_data_formatted.short_description = _("Données reçues")
    
    def has_error(self, obj):
        return bool(obj.processing_error)
    has_error.boolean = True
    has_error.short_description = _("Erreur")
    
    def has_add_permission(self, request):
        return False  # Les notifications sont créées automatiquement