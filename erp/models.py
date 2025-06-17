from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel

class Department(models.Model):
    """
    Départements de l'entreprise.
    """
    name = models.CharField(_("Nom"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Département")
        verbose_name_plural = _("Départements")

class Employee(TimeStampedModel):
    """
    Employés de l'entreprise.
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='employee_profile',
        verbose_name=_("Utilisateur")
    )
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='employees',
        verbose_name=_("Département")
    )
    position = models.CharField(_("Poste"), max_length=100)
    hire_date = models.DateField(_("Date d'embauche"))
    phone = models.CharField(_("Téléphone"), max_length=30)
    emergency_contact = models.CharField(_("Contact d'urgence"), max_length=100, blank=True)
    
    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    class Meta:
        verbose_name = _("Employé")
        verbose_name_plural = _("Employés")

class Transaction(TimeStampedModel):
    """
    Transactions financières internes.
    """
    TYPE_CHOICES = (
        ('income', _('Revenu')),
        ('expense', _('Dépense')),
    )
    
    type = models.CharField(_("Type"), max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(_("Montant"), max_digits=10, decimal_places=2)
    description = models.TextField(_("Description"))
    date = models.DateField(_("Date"))
    recorded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='recorded_transactions',
        verbose_name=_("Enregistré par")
    )
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.amount} - {self.date}"
    
    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

class Asset(TimeStampedModel):
    """
    Actifs/matériels de l'entreprise.
    """
    CATEGORY_CHOICES = (
        ('computer', _('Ordinateur')),
        ('furniture', _('Mobilier')),
        ('vehicle', _('Véhicule')),
        ('equipment', _('Équipement')),
        ('other', _('Autre')),
    )
    
    name = models.CharField(_("Nom"), max_length=100)
    category = models.CharField(_("Catégorie"), max_length=20, choices=CATEGORY_CHOICES)
    acquisition_date = models.DateField(_("Date d'acquisition"))
    value = models.DecimalField(_("Valeur"), max_digits=10, decimal_places=2)
    responsible = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='assigned_assets',
        verbose_name=_("Responsable")
    )
    description = models.TextField(_("Description"), blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"
    
    class Meta:
        verbose_name = _("Actif")
        verbose_name_plural = _("Actifs")