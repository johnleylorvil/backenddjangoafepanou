# payments/serializers.py
from rest_framework import serializers
from .models import PaymentTransaction
from marketplace.models import Order

class CreatePaymentSerializer(serializers.Serializer):
    """
    Serializer pour initier un paiement MonCash.
    """
    order_id = serializers.IntegerField()
    
    def validate_order_id(self, value):
        # Vérifier que la commande existe et appartient à l'utilisateur
        try:
            user = self.context['request'].user
            order = Order.objects.get(id=value, customer=user)
            
            # Vérifier que la commande est en attente de paiement
            if order.status != 'pending':
                raise serializers.ValidationError("Cette commande n'est pas en attente de paiement.")
            
            # Vérifier si un paiement est déjà en cours
            existing_payment = PaymentTransaction.objects.filter(
                order=order, 
                status__in=['initiated', 'pending']
            ).first()
            
            if existing_payment:
                raise serializers.ValidationError("Un paiement est déjà en cours pour cette commande.")
            
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Commande non trouvée.")

class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les transactions de paiement.
    """
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id', 'order_id', 'order_number', 'amount', 'status', 'status_display',
            'transaction_id', 'payment_url', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

class PaymentStatusSerializer(serializers.Serializer):
    """
    Serializer pour vérifier le statut d'un paiement.
    """
    transaction_id = serializers.CharField(required=False)
    order_id = serializers.CharField(required=False)
    
    def validate(self, data):
        transaction_id = data.get('transaction_id')
        order_id = data.get('order_id')
        
        if not transaction_id and not order_id:
            raise serializers.ValidationError(
                "Vous devez fournir soit transaction_id soit order_id."
            )
        
        return data