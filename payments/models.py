from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import uuid

from core.models import TimeStampedModel
from marketplace.models import Order

def generate_order_id():
    """Génère un ID de commande unique"""
    return f"ORD-{uuid.uuid4().hex[:12].upper()}"

class PaymentTransaction(TimeStampedModel):
    """
    Transactions de paiement via MonCash.
    """
    STATUS_CHOICES = (
        ('initiated', _('Initiée')),
        ('pending', _('En attente')),
        ('processing', _('En cours de traitement')),
        ('success', _('Succès')),
        ('failed', _('Échec')),
        ('cancelled', _('Annulée')),
        ('expired', _('Expirée')),
        ('refunded', _('Remboursée')),
    )
    
    PAYMENT_TYPE_CHOICES = (
        ('payment', _('Paiement entrant')),
        ('payout', _('Paiement sortant')),
        ('refund', _('Remboursement')),
    )
    
    # Relations
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE, 
        related_name='payment_transactions', 
        verbose_name=_("Commande")
    )
    
    # Informations de base
    external_order_id = models.CharField(
        _("ID de commande généré"), 
        max_length=100, 
        unique=True,
        default=generate_order_id  # Utilisez la fonction au lieu de lambda
    )
    payment_type = models.CharField(
        _("Type de paiement"),
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='payment'
    )
    amount = models.DecimalField(_("Montant"), max_digits=12, decimal_places=2)
    currency = models.CharField(_("Devise"), max_length=3, default='HTG')
    
    # Statut et tracking
    status = models.CharField(
        _("Statut"), 
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='initiated'
    )
    
    # Identifiants MonCash
    transaction_id = models.CharField(
        _("ID de transaction MonCash"), 
        max_length=100, 
        blank=True,
        db_index=True
    )
    reference = models.CharField(
        _("Référence MonCash"), 
        max_length=100, 
        blank=True,
        db_index=True
    )
    payment_token = models.CharField(_("Token de paiement"), max_length=500, blank=True)
    
    # Informations sur le payeur
    payer_phone = models.CharField(_("Téléphone du payeur"), max_length=30, blank=True)
    payer_account = models.CharField(_("Compte MonCash du payeur"), max_length=50, blank=True)
    
    # Timestamps critiques
    payment_initiated_at = models.DateTimeField(_("Paiement initié le"), auto_now_add=True)
    payment_completed_at = models.DateTimeField(_("Paiement complété le"), null=True, blank=True)
    payment_expires_at = models.DateTimeField(_("Expire le"), null=True, blank=True)
    
    # Réponses et logs de l'API
    response_message = models.TextField(_("Message de réponse"), blank=True)
    response_code = models.CharField(_("Code de réponse"), max_length=10, blank=True)
    api_response_data = models.JSONField(
        _("Données de réponse API"), 
        blank=True, 
        null=True,
        help_text=_("Stockage complet de la réponse API pour debugging")
    )
    
    # URLs de redirection
    return_url = models.URLField(_("URL de retour"), blank=True)
    redirect_url = models.URLField(_("URL de redirection MonCash"), blank=True)
    
    # Tentatives et retry logic
    retry_count = models.PositiveIntegerField(_("Nombre de tentatives"), default=0)
    max_retries = models.PositiveIntegerField(_("Tentatives max"), default=3)
    
    # Métadonnées
    user_agent = models.TextField(_("User Agent"), blank=True)
    ip_address = models.GenericIPAddressField(_("Adresse IP"), null=True, blank=True)
    
    # Audit trail
    error_details = models.TextField(_("Détails d'erreur"), blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    
    def save(self, *args, **kwargs):
        # Auto-générer external_order_id si vide
        if not self.external_order_id:
            self.external_order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
        
        # Définir la date d'expiration (10 minutes pour MonCash)
        if not self.payment_expires_at and self.status == 'initiated':
            self.payment_expires_at = timezone.now() + timezone.timedelta(minutes=10)
        
        # Marquer comme complété si succès
        if self.status == 'success' and not self.payment_completed_at:
            self.payment_completed_at = timezone.now()
            
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Vérifie si le paiement a expiré"""
        if self.payment_expires_at:
            return timezone.now() > self.payment_expires_at
        return False
    
    @property
    def is_successful(self):
        """Vérifie si le paiement est réussi"""
        return self.status == 'success'
    
    @property
    def is_pending(self):
        """Vérifie si le paiement est en attente"""
        return self.status in ['initiated', 'pending', 'processing']
    
    @property
    def can_retry(self):
        """Vérifie si on peut réessayer le paiement"""
        return (
            self.status in ['failed', 'expired'] and 
            self.retry_count < self.max_retries
        )
    
    def mark_as_expired(self):
        """Marque la transaction comme expirée"""
        if self.is_pending and self.is_expired:
            self.status = 'expired'
            self.save(update_fields=['status'])
    
    def increment_retry(self):
        """Incrémente le compteur de tentatives"""
        self.retry_count += 1
        self.save(update_fields=['retry_count'])
    
    def get_gateway_url(self):
        """Génère l'URL de redirection vers MonCash"""
        if self.payment_token:
            base_url = settings.MONCASH_GATEWAY_BASE_URL
            return f"{base_url}/Payment/Redirect?token={self.payment_token}"
        return None
    
    def __str__(self):
        return f"Paiement {self.get_status_display()} - {self.amount} HTG - Commande #{self.order.order_number}"
    
    class Meta:
        verbose_name = _("Transaction de paiement")
        verbose_name_plural = _("Transactions de paiement")
        ordering = ['-created_at']  # ← Changez ici en '-created_at'
        indexes = [
            models.Index(fields=['status', 'created_at']),  # ← Changez ici
            models.Index(fields=['transaction_id']),
            models.Index(fields=['external_order_id']),
            models.Index(fields=['payment_expires_at']),
        ]


# Modèle pour l'historique des changements de statut
class PaymentStatusHistory(models.Model):
    """
    Historique des changements de statut pour audit trail
    """
    transaction = models.ForeignKey(
        PaymentTransaction, 
        on_delete=models.CASCADE, 
        related_name='status_history'
    )
    old_status = models.CharField(_("Ancien statut"), max_length=15)
    new_status = models.CharField(_("Nouveau statut"), max_length=15)
    changed_at = models.DateTimeField(_("Changé le"), auto_now_add=True)
    reason = models.TextField(_("Raison du changement"), blank=True)
    changed_by = models.CharField(_("Changé par"), max_length=100, blank=True)
    
    class Meta:
        verbose_name = _("Historique de statut")
        verbose_name_plural = _("Historiques de statut")
        ordering = ['-changed_at']


# Modèle pour les webhooks/notifications MonCash
class PaymentNotification(models.Model):
    """
    Notifications reçues de MonCash (webhooks)
    """
    transaction = models.ForeignKey(
        PaymentTransaction, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        null=True, blank=True
    )
    received_at = models.DateTimeField(_("Reçu le"), auto_now_add=True)
    raw_data = models.JSONField(_("Données brutes"))
    processed = models.BooleanField(_("Traité"), default=False)
    processing_error = models.TextField(_("Erreur de traitement"), blank=True)
    
    class Meta:
        verbose_name = _("Notification de paiement")
        verbose_name_plural = _("Notifications de paiement")
        ordering = ['-received_at']