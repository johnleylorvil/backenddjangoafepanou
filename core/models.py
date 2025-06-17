from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    """
    Modèle abstrait fournissant des champs de date de création et modification.
    """
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Date de modification"), auto_now=True)

    class Meta:
        abstract = True
        
class UserProfile(models.Model):
    """
    Extension du modèle User de Django pour les informations additionnelles.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        verbose_name=_("Utilisateur")
    )
    phone = models.CharField(_("Téléphone"), max_length=30, blank=True)
    address = models.TextField(_("Adresse"), blank=True)
    is_vendor = models.BooleanField(_("Est vendeur"), default=False)
    is_employee = models.BooleanField(_("Est employé"), default=False)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    class Meta:
        verbose_name = _("Profil utilisateur")
        verbose_name_plural = _("Profils utilisateurs")