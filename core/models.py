from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

class TimeStampedModel(models.Model):
    """
    Modèle abstrait fournissant des champs de date de création et modification.
    """
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Date de modification"), auto_now=True)

    class Meta:
        abstract = True
        
class UserProfile(TimeStampedModel):
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
    date_of_birth = models.DateField(_("Date de naissance"), null=True, blank=True)
    profile_image = models.ImageField(_("Photo de profil"), upload_to='profiles/', null=True, blank=True)
    is_vendor = models.BooleanField(_("Est vendeur"), default=False)
    is_employee = models.BooleanField(_("Est employé"), default=False)
    bio = models.TextField(_("Biographie"), blank=True)
    
    # Paramètres de notification
    email_notifications = models.BooleanField(_("Notifications par email"), default=True)
    sms_notifications = models.BooleanField(_("Notifications par SMS"), default=False)
    
    # Préférences utilisateur
    language = models.CharField(_("Langue préférée"), max_length=10, default='fr', choices=[
        ('fr', _("Français")),
        ('en', _("Anglais")),
        ('ht', _("Créole haïtien"))
    ])
    currency = models.CharField(_("Devise préférée"), max_length=3, default='HTG', choices=[
        ('HTG', _("Gourde haïtienne")),
        ('USD', _("Dollar américain"))
    ])
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    class Meta:
        verbose_name = _("Profil utilisateur")
        verbose_name_plural = _("Profils utilisateurs")


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Crée ou met à jour le profil utilisateur automatiquement"""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        try:
            instance.profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(user=instance)