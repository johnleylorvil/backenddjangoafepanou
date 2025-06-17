from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel
from marketplace.models import Order

class PaymentTransaction(TimeStampedModel):
    """
    Transactions de paiement via MonCash.
    """
    STATUS_CHOICES = (
        ('initiated', _('Initiée')),
        ('pending', _('En attente')),
        ('success', _('Succès')),
        ('failed', _('Échec')),
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions', verbose_name=_("Commande"))
    
    amount = models.DecimalField(_("Montant"), max_digits=10, decimal_places=2)
    status = models.CharField(
        _("Statut"), 
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='initiated'
    )
    transaction_id = models.CharField(_("ID de transaction MonCash"), max_length=100, blank=True)
    external_order_id = models.CharField(_("ID de commande généré"), max_length=100, unique=True)
    payment_token = models.CharField(_("Token de paiement"), max_length=255, blank=True)
    payer_phone = models.CharField(_("Téléphone du payeur"), max_length=30, blank=True)
    
    # Réponses de l'API
    response_message = models.TextField(_("Message de réponse"), blank=True)
    response_code = models.CharField(_("Code de réponse"), max_length=10, blank=True)
    
    def __str__(self):
        return f"Paiement {self.status} pour Commande #{self.order.order_number}"
    
    class Meta:
        verbose_name = _("Transaction de paiement")
        verbose_name_plural = _("Transactions de paiement")