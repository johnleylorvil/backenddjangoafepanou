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

class CustomUserAdmin(BaseUserAdmin):
    """
    Personnalise l'administration de l'utilisateur en ajoutant le profil inline.
    """
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_is_vendor', 'get_is_employee')
    list_filter = BaseUserAdmin.list_filter + ('profile__is_vendor', 'profile__is_employee',)
    search_fields = BaseUserAdmin.search_fields + ('profile__phone',)
    
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
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)

class UserProfileAdmin(admin.ModelAdmin):
    """
    Configuration de l'administration du modèle UserProfile.
    """
    list_display = ('user', 'phone', 'is_vendor', 'is_employee')
    list_filter = ('is_vendor', 'is_employee')
    search_fields = ('user__username', 'user__email', 'phone', 'address')
    raw_id_fields = ('user',)
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        (_('Informations de contact'), {
            'fields': ('phone', 'address')
        }),
        (_('Rôles'), {
            'fields': ('is_vendor', 'is_employee')
        }),
    )

# Réenregistrer le modèle User avec notre classe d'administration personnalisée
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Enregistrer aussi le modèle UserProfile pour un accès direct
admin.site.register(UserProfile, UserProfileAdmin)