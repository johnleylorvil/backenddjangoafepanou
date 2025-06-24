
# serializers.py
from rest_framework import serializers
from decimal import Decimal
from .models import PaymentTransaction
from marketplace.models import Order


class OrderSerializer(serializers.ModelSerializer):
    """Sérializer pour les commandes"""
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'total_amount', 'shipping_cost']
        read_only_fields = ['id', 'order_number']


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """Sérializer pour les transactions de paiement"""
    order_details = OrderSerializer(source='order', read_only=True)
    gateway_url = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'external_order_id', 'amount', 'currency', 'status',
            'transaction_id', 'reference', 'payment_token', 'payer_phone',
            'payment_initiated_at', 'payment_completed_at', 'payment_expires_at',
            'retry_count', 'response_message', 'response_code',
            'order_details', 'gateway_url', 'is_expired'
        ]
        read_only_fields = [
            'id', 'external_order_id', 'transaction_id', 'reference',
            'payment_token', 'payment_initiated_at', 'payment_completed_at',
            'payment_expires_at', 'retry_count', 'response_message', 'response_code'
        ]
    
    def get_gateway_url(self, obj):
        return obj.get_gateway_url()


class CreatePaymentSerializer(serializers.Serializer):
    """Sérializer pour créer un paiement"""
    order_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    return_url = serializers.URLField(required=False)
    
    def validate_order_id(self, value):
        try:
            order = Order.objects.get(id=value)
            if order.status == 'paid':
                raise serializers.ValidationError("Cette commande est déjà payée")
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Commande non trouvée")
    
    def validate_amount(self, value):
        if value and value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0")
        return value


class PaymentStatusSerializer(serializers.Serializer):
    """Sérializer pour vérifier le statut d'un paiement"""
    transaction_id = serializers.CharField(required=False)
    external_order_id = serializers.CharField(required=False)
    
    def validate(self, data):
        if not data.get('transaction_id') and not data.get('external_order_id'):
            raise serializers.ValidationError(
                "Vous devez fournir soit transaction_id soit external_order_id"
            )
        return data


# serializers.py (ajouts)
class CustomerStatusSerializer(serializers.Serializer):
    """Sérializer pour vérifier le statut d'un client MonCash"""
    account = serializers.CharField(max_length=20, help_text="Numéro de téléphone MonCash")


class PayoutSerializer(serializers.Serializer):
    """Sérializer pour créer un payout (paiement sortant)"""
    receiver = serializers.CharField(max_length=20, help_text="Compte MonCash du destinataire")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(max_length=255)
    reference = serializers.CharField(max_length=100, required=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être supérieur à 0")
        return value


class RefundSerializer(serializers.Serializer):
    """Sérializer pour créer un remboursement"""
    transaction_id = serializers.IntegerField(help_text="ID de la transaction à rembourser")
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    reason = serializers.CharField(max_length=255, required=False)
    
    def validate_transaction_id(self, value):
        try:
            transaction = PaymentTransaction.objects.get(id=value, status='success')
            return value
        except PaymentTransaction.DoesNotExist:
            raise serializers.ValidationError("Transaction non trouvée ou non éligible au remboursement")


class BalanceSerializer(serializers.Serializer):
    """Sérializer pour afficher le solde"""
    balance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
    last_updated = serializers.DateTimeField(read_only=True)