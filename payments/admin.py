from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
import csv
import json
from datetime import timedelta

from .models import PaymentTransaction

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_link', 'amount_display', 'status_badge', 'transaction_id', 'payer_phone', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('order__order_number', 'transaction_id', 'external_order_id', 'payer_phone', 'response_message')
    readonly_fields = (
        'created_at', 'updated_at', 'order_details', 'moncash_info',
        'payment_details', 'response_formatted', 'payment_url'
    )
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('order', 'status', 'amount')
        }),
        (_('Informations MonCash'), {
            'fields': ('transaction_id', 'external_order_id', 'payment_token', 'payer_phone')
        }),
        (_('Détails de la commande'), {
            'fields': ('order_details',)
        }),
        (_('Informations de paiement'), {
            'fields': ('payment_details', 'payment_url')
        }),
        (_('Réponse de l\'API'), {
            'fields': ('response_message', 'response_code', 'response_formatted')
        }),
        (_('Statistiques et aperçu'), {
            'fields': ('moncash_info',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:marketplace_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return "-"
    order_link.short_description = _("Commande")
    order_link.admin_order_field = 'order__order_number'
    
    def amount_display(self, obj):
        return format_html('<strong>{} HTG</strong>', obj.amount)
    amount_display.short_description = _("Montant")
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        status_colors = {
            'initiated': '#f39c12',  # Orange
            'pending': '#3498db',    # Bleu
            'success': '#2ecc71',    # Vert
            'failed': '#e74c3c'      # Rouge
        }
        color = status_colors.get(obj.status, '#95a5a6')  # Gris par défaut
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _("Statut")
    status_badge.admin_order_field = 'status'
    
    def response_formatted(self, obj):
        """Affiche la réponse JSON formatée de manière lisible"""
        if not obj.response_message:
            return "-"
        
        try:
            # Essayer de parser comme JSON
            response_data = json.loads(obj.response_message)
            formatted_json = json.dumps(response_data, indent=4)
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', formatted_json)
        except:
            # Si ce n'est pas du JSON, afficher tel quel
            return format_html('<pre style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{}</pre>', obj.response_message)
    response_formatted.short_description = _("Réponse formatée")
    
    def order_details(self, obj):
        """Affiche les détails de la commande associée"""
        if not obj.order:
            return _("Aucune commande associée")
        
        order = obj.order
        items = order.items.all()
        customer = order.customer
        
        html = f"""
        <div style="margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">Détails de la commande #{order.order_number}</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">
                <tr>
                    <td style="padding: 5px 10px 5px 0; width: 150px;"><strong>Client:</strong></td>
                    <td>{customer.get_full_name() or customer.username}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Statut de commande:</strong></td>
                    <td>{order.get_status_display()}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Date de commande:</strong></td>
                    <td>{order.created_at.strftime('%d/%m/%Y %H:%M')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Montant total:</strong></td>
                    <td><strong>{order.total_amount} HTG</strong></td>
                </tr>
            </table>
            
            <h4 style="margin-bottom: 10px;">Articles commandés:</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <thead>
                    <tr style="background-color: #eee;">
                        <th style="padding: 8px; text-align: left; border-bottom: 1px solid #ddd;">Produit</th>
                        <th style="padding: 8px; text-align: center; border-bottom: 1px solid #ddd;">Qté</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">Prix</th>
                        <th style="padding: 8px; text-align: right; border-bottom: 1px solid #ddd;">Total</th>
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
        
        html += """
                </tbody>
            </table>
        </div>
        """
        
        return format_html(html)
    order_details.short_description = _("Détails de la commande")
    
    def payment_details(self, obj):
        """Affiche les détails du paiement"""
        if obj.status == 'initiated':
            status_color = "#f39c12"  # Orange
            status_text = "Initiée"
        elif obj.status == 'pending':
            status_color = "#3498db"  # Bleu
            status_text = "En attente"
        elif obj.status == 'success':
            status_color = "#2ecc71"  # Vert
            status_text = "Réussie"
        else:
            status_color = "#e74c3c"  # Rouge
            status_text = "Échouée"
        
        html = f"""
        <div style="margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">Détails du paiement</h3>
            <div style="margin-bottom: 15px;">
                <span style="background-color: {status_color}; color: white; padding: 5px 10px; border-radius: 5px; font-weight: bold;">
                    Transaction {status_text}
                </span>
            </div>
            
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px 10px 5px 0; width: 200px;"><strong>Montant:</strong></td>
                    <td><strong>{obj.amount} HTG</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>ID de transaction MonCash:</strong></td>
                    <td>{obj.transaction_id or '-'}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>ID de commande externe:</strong></td>
                    <td>{obj.external_order_id}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Téléphone du payeur:</strong></td>
                    <td>{obj.payer_phone or '-'}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Token de paiement:</strong></td>
                    <td style="word-break: break-all;">{obj.payment_token or '-'}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Code de réponse:</strong></td>
                    <td>{obj.response_code or '-'}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Date de création:</strong></td>
                    <td>{obj.created_at.strftime('%d/%m/%Y %H:%M:%S')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 10px 5px 0;"><strong>Dernière mise à jour:</strong></td>
                    <td>{obj.updated_at.strftime('%d/%m/%Y %H:%M:%S')}</td>
                </tr>
            </table>
        </div>
        """
        
        return format_html(html)
    payment_details.short_description = _("Détails du paiement")
    
    def payment_url(self, obj):
        """Génère l'URL de paiement MonCash si disponible"""
        if not obj.payment_token:
            return _("Aucun token de paiement disponible")
        
        redirect_url = f"https://moncashbutton.digicelgroup.com/Moncash-middleware/Payment/Redirect?token={obj.payment_token}"
        
        html = f"""
        <div style="margin-top: 10px;">
            <a href="{redirect_url}" target="_blank" style="
                display: inline-block;
                background-color: #FF0000;
                color: white;
                padding: 10px 15px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
            ">
                Accéder au paiement MonCash
            </a>
            <p style="margin-top: 5px; color: #666;">
                <small>URL: {redirect_url}</small>
            </p>
        </div>
        """
        
        return format_html(html)
    payment_url.short_description = _("URL de paiement")
    
    def moncash_info(self, obj):
        """Affiche des statistiques et informations sur MonCash"""
        # Obtenir les statistiques de paiement
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        
        total_success = PaymentTransaction.objects.filter(status='success').count()
        total_pending = PaymentTransaction.objects.filter(status='pending').count()
        total_failed = PaymentTransaction.objects.filter(status='failed').count()
        total_all = PaymentTransaction.objects.count()
        
        success_rate = (total_success / total_all * 100) if total_all > 0 else 0
        
        # Paiements des 30 derniers jours
        recent_success = PaymentTransaction.objects.filter(
            status='success', created_at__date__gte=last_30_days
        ).count()
        
        recent_total = PaymentTransaction.objects.filter(
            created_at__date__gte=last_30_days
        ).count()
        
        recent_success_rate = (recent_success / recent_total * 100) if recent_total > 0 else 0
        
        # Montant total des paiements réussis
        total_amount = PaymentTransaction.objects.filter(
            status='success'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        recent_amount = PaymentTransaction.objects.filter(
            status='success', created_at__date__gte=last_30_days
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        html = f"""
        <div style="margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">Statistiques de paiement MonCash</h3>
            
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px;">
                <div style="background-color: #2ecc71; color: white; padding: 15px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_success}</div>
                    <div>Paiements réussis</div>
                </div>
                <div style="background-color: #3498db; color: white; padding: 15px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_pending}</div>
                    <div>Paiements en attente</div>
                </div>
                <div style="background-color: #e74c3c; color: white; padding: 15px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_failed}</div>
                    <div>Paiements échoués</div>
                </div>
                <div style="background-color: #9b59b6; color: white; padding: 15px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold;">{total_amount:,.2f} HTG</div>
                    <div>Montant total perçu</div>
                </div>
            </div>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Taux de réussite global:</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                        <div style="width: 100%; height: 20px; background-color: #f1f1f1; border-radius: 10px; overflow: hidden;">
                            <div style="width: {success_rate}%; height: 100%; background-color: #2ecc71; border-radius: 10px;"></div>
                        </div>
                        <div style="text-align: center; margin-top: 5px;">{success_rate:.1f}%</div>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Taux de réussite (30 derniers jours):</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                        <div style="width: 100%; height: 20px; background-color: #f1f1f1; border-radius: 10px; overflow: hidden;">
                            <div style="width: {recent_success_rate}%; height: 100%; background-color: #3498db; border-radius: 10px;"></div>
                        </div>
                        <div style="text-align: center; margin-top: 5px;">{recent_success_rate:.1f}%</div>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Montant perçu (30 derniers jours):</strong></td>
                    <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>{recent_amount:,.2f} HTG</strong></td>
                </tr>
            </table>
            
            <div style="background-color: #f39c12; color: white; padding: 10px; border-radius: 5px; margin-bottom: 15px;">
                <strong>💡 Note:</strong> Pour plus d'informations sur l'API MonCash, consultez la 
                <a href="https://moncashbutton.digicelgroup.com/Moncash-business/api" target="_blank" style="color: white; text-decoration: underline;">
                    documentation officielle
                </a>.
            </div>
        </div>
        """
        
        return format_html(html)
    moncash_info.short_description = _("Informations MonCash")
    
    actions = ['mark_as_success', 'mark_as_failed', 'mark_as_pending', 'export_transactions_csv']
    
    def mark_as_success(self, request, queryset):
        updated = queryset.exclude(status='success').update(status='success')
        self.message_user(request, _(f"{updated} transaction(s) ont été marquées comme réussies."))
    mark_as_success.short_description = _("Marquer comme réussies")
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.exclude(status__in=['failed', 'success']).update(status='failed')
        self.message_user(request, _(f"{updated} transaction(s) ont été marquées comme échouées."))
    mark_as_failed.short_description = _("Marquer comme échouées")
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.filter(status='initiated').update(status='pending')
        self.message_user(request, _(f"{updated} transaction(s) ont été marquées comme en attente."))
    mark_as_pending.short_description = _("Marquer comme en attente")
    
    def export_transactions_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="moncash_transactions.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Numéro de commande', 'Montant', 'Statut', 
            'ID de transaction MonCash', 'ID de commande externe',
            'Téléphone du payeur', 'Date de création', 'Code de réponse'
        ])
        
        for transaction in queryset:
            writer.writerow([
                transaction.id,
                transaction.order.order_number if transaction.order else '-',
                transaction.amount,
                transaction.get_status_display(),
                transaction.transaction_id or '-',
                transaction.external_order_id,
                transaction.payer_phone or '-',
                transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                transaction.response_code or '-'
            ])
        
        return response
    export_transactions_csv.short_description = _("Exporter les transactions sélectionnées en CSV")
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'dashboard/',
                self.admin_site.admin_view(self.moncash_dashboard_view),
                name='payments_moncash_dashboard'
            ),
            path(
                'documentation/',
                self.admin_site.admin_view(self.moncash_documentation_view),
                name='payments_moncash_documentation'
            ),
        ]
        return custom_urls + urls
    
    def moncash_dashboard_view(self, request):
        """Vue de tableau de bord pour les paiements MonCash"""
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        # Obtenir des statistiques pour le tableau de bord
        today = timezone.now().date()
        start_of_month = today.replace(day=1)
        last_month = (start_of_month - timedelta(days=1)).replace(day=1)
        
        # Statistiques du mois en cours
        current_month_stats = {
            'success': PaymentTransaction.objects.filter(
                status='success', created_at__date__gte=start_of_month
            ).count(),
            'pending': PaymentTransaction.objects.filter(
                status='pending', created_at__date__gte=start_of_month
            ).count(),
            'failed': PaymentTransaction.objects.filter(
                status='failed', created_at__date__gte=start_of_month
            ).count(),
            'total': PaymentTransaction.objects.filter(
                created_at__date__gte=start_of_month
            ).count(),
            'amount': PaymentTransaction.objects.filter(
                status='success', created_at__date__gte=start_of_month
            ).aggregate(total=Sum('amount'))['total'] or 0
        }
        
        # Statistiques du mois précédent
        previous_month_stats = {
            'success': PaymentTransaction.objects.filter(
                status='success', 
                created_at__date__gte=last_month,
                created_at__date__lt=start_of_month
            ).count(),
            'amount': PaymentTransaction.objects.filter(
                status='success', 
                created_at__date__gte=last_month,
                created_at__date__lt=start_of_month
            ).aggregate(total=Sum('amount'))['total'] or 0
        }
        
        # Calculer les variations
        success_variation = 0
        amount_variation = 0
        
        if previous_month_stats['success'] > 0:
            success_variation = (current_month_stats['success'] - previous_month_stats['success']) / previous_month_stats['success'] * 100
        
        if previous_month_stats['amount'] > 0:
            amount_variation = (current_month_stats['amount'] - previous_month_stats['amount']) / previous_month_stats['amount'] * 100
        
        context = {
            'title': _("Tableau de bord MonCash"),
            'current_month': today.strftime('%B %Y'),
            'current_stats': current_month_stats,
            'success_variation': success_variation,
            'amount_variation': amount_variation,
            'has_permission': True,
            'opts': self.model._meta,
        }
        
        content = render_to_string('admin/payments/moncash_dashboard.html', context)
        return HttpResponse(content)
    
    def moncash_documentation_view(self, request):
        """Vue de documentation pour l'intégration MonCash"""
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        context = {
            'title': _("Documentation MonCash"),
            'has_permission': True,
            'opts': self.model._meta,
        }
        
        content = render_to_string('admin/payments/moncash_documentation.html', context)
        return HttpResponse(content)
    
    def changelist_view(self, request, extra_context=None):
        """Personnalisation de la vue de liste des transactions"""
        # Ajouter des liens vers le tableau de bord et la documentation
        extra_context = extra_context or {}
        
        dashboard_url = reverse('admin:payments_moncash_dashboard')
        documentation_url = reverse('admin:payments_moncash_documentation')
        
        extra_context.update({
            'dashboard_url': dashboard_url,
            'documentation_url': documentation_url,
        })
        
        return super().changelist_view(request, extra_context=extra_context)

# Templates nécessaires:
# templates/admin/payments/moncash_dashboard.html
# templates/admin/payments/moncash_documentation.html