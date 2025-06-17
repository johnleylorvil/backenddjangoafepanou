from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    """
    Affiche le profil utilisateur comme un élément inline dans l'administration de l'utilisateur.
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = _('Profil')
    fk_name = 'user'
    
    fieldsets = (
        (None, {
            'fields': ('phone', 'address', 'date_of_birth', 'profile_image', 'bio')
        }),
        (_('Rôles'), {
            'fields': ('is_vendor', 'is_employee')
        }),
        (_('Préférences'), {
            'fields': ('language', 'currency', 'email_notifications', 'sms_notifications')
        }),
    )

class CustomUserAdmin(BaseUserAdmin):
    """
    Personnalise l'administration de l'utilisateur en ajoutant le profil inline.
    """
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 
                   'get_is_vendor', 'get_is_employee', 'get_language', 'get_phone')
    list_filter = BaseUserAdmin.list_filter + ('profile__is_vendor', 'profile__is_employee', 
                                             'profile__language', 'profile__currency')
    search_fields = BaseUserAdmin.search_fields + ('profile__phone', 'profile__address', 'profile__bio')
    
    def get_is_vendor(self, obj):
        try:
            return obj.profile.is_vendor
        except UserProfile.DoesNotExist:
            return False
    get_is_vendor.short_description = _('Vendeur')
    get_is_vendor.boolean = True
    
    def get_is_employee(self, obj):
        try:
            return obj.profile.is_employee
        except UserProfile.DoesNotExist:
            return False
    get_is_employee.short_description = _('Employé')
    get_is_employee.boolean = True
    
    def get_language(self, obj):
        try:
            return obj.profile.get_language_display()
        except UserProfile.DoesNotExist:
            return ''
    get_language.short_description = _('Langue')
    
    def get_phone(self, obj):
        try:
            return obj.profile.phone
        except UserProfile.DoesNotExist:
            return ''
    get_phone.short_description = _('Téléphone')
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

class UserProfileAdmin(admin.ModelAdmin):
    """
    Configuration de l'administration du modèle UserProfile.
    """
    list_display = ('user', 'phone', 'language', 'currency', 'is_vendor', 'is_employee', 'created_at')
    list_filter = ('is_vendor', 'is_employee', 'language', 'currency', 'email_notifications', 'sms_notifications')
    search_fields = ('user__username', 'user__email', 'phone', 'address', 'bio')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        (_('Informations personnelles'), {
            'fields': ('phone', 'address', 'date_of_birth', 'profile_image', 'bio')
        }),
        (_('Rôles'), {
            'fields': ('is_vendor', 'is_employee')
        }),
        (_('Préférences'), {
            'fields': ('language', 'currency', 'email_notifications', 'sms_notifications')
        }),
        (_('Horodatage'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# Réenregistrer le modèle User avec notre classe d'administration personnalisée
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Enregistrer aussi le modèle UserProfile pour un accès direct
admin.site.register(UserProfile, UserProfileAdmin)