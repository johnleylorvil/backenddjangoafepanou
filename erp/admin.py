from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Department, Employee, Transaction, Asset

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_count', 'description_preview')
    search_fields = ('name', 'description')
    
    def employee_count(self, obj):
        return obj.employees.count()
    employee_count.short_description = _("Nombre d'employés")
    
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
        return "-"
    description_preview.short_description = _("Description")
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            employee_count=Count('employees')
        )
        return queryset
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
    )

class EmployeeAssetInline(admin.TabularInline):
    model = Asset
    fk_name = 'responsible'
    extra = 0
    fields = ('name', 'category', 'acquisition_date', 'value')
    readonly_fields = ('acquisition_date',)
    verbose_name = _("Actif assigné")
    verbose_name_plural = _("Actifs assignés")
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'department', 'position', 'hire_date', 'phone', 'asset_count', 'status_indicator')
    list_filter = ('department', 'hire_date')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'position', 'phone')
    date_hierarchy = 'hire_date'
    raw_id_fields = ('user',)
    inlines = [EmployeeAssetInline]
    
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    full_name.short_description = _("Nom complet")
    
    def asset_count(self, obj):
        count = obj.assigned_assets.count()
        if count > 0:
            return format_html(
                '<a href="{}?responsible__id__exact={}">{}</a>',
                reverse('admin:erp_asset_changelist'),
                obj.id,
                count
            )
        return count
    asset_count.short_description = _("Actifs")
    
    def status_indicator(self, obj):
        # Employé récent (moins de 3 mois)
        three_months_ago = timezone.now().date() - timedelta(days=90)
        if obj.hire_date >= three_months_ago:
            return format_html('<span style="color: #2ecc71;">●</span> <span style="color: #2ecc71;">Nouveau</span>')
        # Employé expérimenté (plus d'un an)
        one_year_ago = timezone.now().date() - timedelta(days=365)
        if obj.hire_date <= one_year_ago:
            return format_html('<span style="color: #3498db;">●</span> <span style="color: #3498db;">Expérimenté</span>')
        return format_html('<span style="color: #f39c12;">●</span> <span style="color: #f39c12;">Régulier</span>')
    status_indicator.short_description = _("Statut")
    
    fieldsets = (
        (None, {
            'fields': ('user', 'department', 'position')
        }),
        (_('Informations personnelles'), {
            'fields': ('hire_date', 'phone', 'emergency_contact')
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'type_colored', 'amount_formatted', 'description_preview', 'date', 'recorded_by')
    list_filter = ('type', 'date', 'recorded_by')
    search_fields = ('description', 'recorded_by__username')
    date_hierarchy = 'date'
    
    def type_colored(self, obj):
        if obj.type == 'income':
            return format_html('<span style="color: #2ecc71; font-weight: bold;">{}</span>', obj.get_type_display())
        return format_html('<span style="color: #e74c3c; font-weight: bold;">{}</span>', obj.get_type_display())
    type_colored.short_description = _("Type")
    
    def amount_formatted(self, obj):
        if obj.type == 'income':
            return format_html('<span style="color: #2ecc71; font-weight: bold;">+{} HTG</span>', obj.amount)
        return format_html('<span style="color: #e74c3c; font-weight: bold;">-{} HTG</span>', obj.amount)
    amount_formatted.short_description = _("Montant")
    
    def description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return "-"
    description_preview.short_description = _("Description")
    
    fieldsets = (
        (None, {
            'fields': ('type', 'amount', 'description')
        }),
        (_('Détails'), {
            'fields': ('date', 'recorded_by', 'financial_summary')
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'financial_summary')
    
    def financial_summary(self, obj):
        # Si c'est un nouvel objet, pas encore de résumé
        if not obj.pk:
            return _("Disponible après enregistrement")
        
        # Calcul des totaux pour le mois en cours
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        
        income_month = Transaction.objects.filter(
            type='income', 
            date__gte=first_day_of_month, 
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        expense_month = Transaction.objects.filter(
            type='expense', 
            date__gte=first_day_of_month, 
            date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        balance_month = income_month - expense_month
        
        # Représentation HTML du résumé
        html = f"""
        <div style="margin-top: 10px; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
            <h3 style="margin-top: 0;">Résumé financier du mois</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>Revenus:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #ddd; color: #2ecc71; text-align: right; font-weight: bold;">+{income_month} HTG</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>Dépenses:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #ddd; color: #e74c3c; text-align: right; font-weight: bold;">-{expense_month} HTG</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Solde:</strong></td>
                    <td style="padding: 8px 0; text-align: right; font-weight: bold; color: {'#2ecc71' if balance_month >= 0 else '#e74c3c'};">
                        {balance_month} HTG
                    </td>
                </tr>
            </table>
        </div>
        """
        return format_html(html)
    financial_summary.short_description = _("Résumé financier")
    
    def save_model(self, request, obj, form, change):
        if not obj.recorded_by:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['export_csv']
    
    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="transactions.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Type', 'Montant', 'Description', 'Date', 'Enregistré par'])
        
        for transaction in queryset:
            writer.writerow([
                transaction.id,
                transaction.get_type_display(),
                transaction.amount,
                transaction.description,
                transaction.date,
                transaction.recorded_by.username if transaction.recorded_by else ''
            ])
        
        return response
    export_csv.short_description = _("Exporter les transactions sélectionnées en CSV")

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_badge', 'acquisition_date', 'value_formatted', 'responsible', 'age')
    list_filter = ('category', 'acquisition_date')
    search_fields = ('name', 'description', 'responsible__user__username', 'responsible__user__first_name', 'responsible__user__last_name')
    date_hierarchy = 'acquisition_date'
    
    def category_badge(self, obj):
        category_colors = {
            'computer': '#3498db',
            'furniture': '#f39c12',
            'vehicle': '#e74c3c',
            'equipment': '#2ecc71',
            'other': '#95a5a6'
        }
        color = category_colors.get(obj.category, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = _("Catégorie")
    
    def value_formatted(self, obj):
        return f"{obj.value} HTG"
    value_formatted.short_description = _("Valeur")
    
    def age(self, obj):
        days = (timezone.now().date() - obj.acquisition_date).days
        if days < 30:
            return _("Neuf (moins d'un mois)")
        elif days < 365:
            months = days // 30
            return _("{} mois").format(months)
        else:
            years = days // 365
            return _("{} an(s)").format(years)
    age.short_description = _("Âge")
    
    fieldsets = (
        (None, {
            'fields': ('name', 'category', 'description')
        }),
        (_('Informations financières'), {
            'fields': ('acquisition_date', 'value')
        }),
        (_('Attribution'), {
            'fields': ('responsible',)
        }),
        (_('Informations système'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

# Personnalisation de la page d'accueil de l'admin Django
class ERPAdminSite(admin.AdminSite):
    site_header = _("Administration Afè Pa Nou")
    site_title = _("Afè Pa Nou ERP")
    index_title = _("Tableau de bord")

# Pour utiliser ce site personnalisé, décommentez ces lignes dans votre apps.py
# et mettez à jour votre urls.py principal pour utiliser ce site admin au lieu du site par défaut
# 
# from django.apps import AppConfig
# class ErpConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'erp'
#     
#     def ready(self):
#         from .admin import ERPAdminSite
#         from django.contrib import admin
#         admin.site = ERPAdminSite()
#         admin.sites.site = admin.site