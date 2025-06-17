# payments/views.py
import uuid
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .models import PaymentTransaction
from .serializers import CreatePaymentSerializer, PaymentTransactionSerializer, PaymentStatusSerializer
from .services import MonCashService
from marketplace.models import Order

class PaymentViewSet(viewsets.GenericViewSet):
    """
    API pour les paiements MonCash.
    
    create:
    Initie un paiement MonCash pour une commande.
    
    transactions:
    Liste les transactions de paiement de l'utilisateur.
    
    status:
    Vérifie le statut d'un paiement par transaction_id ou order_id.
    
    callback:
    Endpoint de callback pour les notifications MonCash.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePaymentSerializer
        elif self.action == 'status':
            return PaymentStatusSerializer
        return PaymentTransactionSerializer
    
    def get_queryset(self):
        """
        Retourne uniquement les transactions de paiement de l'utilisateur courant.
        """
        return PaymentTransaction.objects.filter(user=self.request.user)
    
    def create(self, request):
        """
        Initie un paiement MonCash pour une commande.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data['order_id']
        order = Order.objects.get(id=order_id, customer=request.user)
        
        # Générer un ID de commande unique pour MonCash
        moncash_order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        
        # Créer une transaction de paiement
        transaction = PaymentTransaction.objects.create(
            order=order,
            user=request.user,
            amount=order.total_amount,
            order_id=moncash_order_id,
            status='initiated'
        )
        
        try:
            # Appeler le service MonCash pour créer un paiement
            moncash_service = MonCashService()
            payment_data = moncash_service.create_payment(
                order_id=moncash_order_id,
                amount=float(order.total_amount)
            )
            
            # Mettre à jour la transaction avec les données de paiement
            transaction.payment_token = payment_data['payment_token']
            transaction.payment_url = payment_data['payment_url']
            transaction.api_response = payment_data['response']
            transaction.status = 'pending'
            transaction.save()
            
            # Retourner les informations de paiement
            return Response({
                'success': True,
                'message': 'Paiement initié avec succès',
                'payment_url': payment_data['payment_url'],
                'transaction_id': transaction.id
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # En cas d'erreur, mettre à jour la transaction
            transaction.status = 'failed'
            transaction.error_message = str(e)
            transaction.save()
            
            return Response({
                'success': False,
                'message': 'Erreur lors de l\'initiation du paiement',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """
        Liste les transactions de paiement de l'utilisateur.
        """
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = PaymentTransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = PaymentTransactionSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def status(self, request):
        """
        Vérifie le statut d'un paiement par transaction_id ou order_id.
        """
        serializer = PaymentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        transaction_id = serializer.validated_data.get('transaction_id')
        order_id = serializer.validated_data.get('order_id')
        
        moncash_service = MonCashService()
        
        try:
            if transaction_id:
                # Vérifier par transaction_id
                payment_info = moncash_service.check_payment_by_transaction_id(transaction_id)
                
                # Trouver et mettre à jour la transaction correspondante
                transaction = PaymentTransaction.objects.filter(
                    transaction_id=transaction_id
                ).first()
                
            else:
                # Vérifier par order_id
                payment_info = moncash_service.check_payment_by_order_id(order_id)
                
                # Trouver et mettre à jour la transaction correspondante
                transaction = PaymentTransaction.objects.filter(
                    order_id=order_id
                ).first()
            
            if transaction:
                # Vérifier que l'utilisateur a accès à cette transaction
                if transaction.user != request.user:
                    return Response({
                        'success': False,
                        'message': 'Vous n\'êtes pas autorisé à accéder à cette transaction'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Mettre à jour la transaction avec les informations du paiement
                payment_details = payment_info.get('payment', {})
                
                if payment_details:
                    transaction.transaction_id = payment_details.get('transaction_id', '')
                    transaction.payer_phone = payment_details.get('payer', '')
                    
                    # Vérifier le statut du paiement
                    message = payment_details.get('message', '').lower()
                    if message == 'successful':
                        transaction.status = 'success'
                        
                        # Mettre à jour le statut de la commande
                        order = transaction.order
                        order.status = 'paid'
                        order.save()
                    
                    transaction.api_response = payment_info
                    transaction.save()
            
            return Response({
                'success': True,
                'payment_info': payment_info,
                'transaction': PaymentTransactionSerializer(transaction).data if transaction else None
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Erreur lors de la vérification du paiement',
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def callback(self, request):
        """
        Endpoint de callback pour les notifications MonCash.
        Cette URL est appelée par MonCash pour notifier le statut d'un paiement.
        """
        # Récupérer les données de la notification
        transaction_id = request.data.get('transactionId')
        order_id = request.data.get('orderId')
        
        if not transaction_id and not order_id:
            return Response({
                'success': False,
                'message': 'Données de notification insuffisantes'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Trouver la transaction correspondante
            if transaction_id:
                transaction = PaymentTransaction.objects.filter(
                    transaction_id=transaction_id
                ).first()
            else:
                transaction = PaymentTransaction.objects.filter(
                    order_id=order_id
                ).first()
            
            if not transaction:
                return Response({
                    'success': False,
                    'message': 'Transaction non trouvée'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Vérifier le statut du paiement avec l'API MonCash
            moncash_service = MonCashService()
            
            if transaction_id:
                payment_info = moncash_service.check_payment_by_transaction_id(transaction_id)
            else:
                payment_info = moncash_service.check_payment_by_order_id(order_id)
            
            # Mettre à jour la transaction avec les informations du paiement
            payment_details = payment_info.get('payment', {})
            
            if payment_details:
                transaction.transaction_id = payment_details.get('transaction_id', '')
                transaction.payer_phone = payment_details.get('payer', '')
                
                # Vérifier le statut du paiement
                message = payment_details.get('message', '').lower()
                if message == 'successful':
                    transaction.status = 'success'
                    
                    # Mettre à jour le statut de la commande
                    order = transaction.order
                    order.status = 'paid'
                    order.save()
                elif message == 'failed':
                    transaction.status = 'failed'
                
                transaction.api_response = payment_info
                transaction.save()
            
            return Response({
                'success': True,
                'message': 'Notification traitée avec succès'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Erreur lors du traitement de la notification',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)