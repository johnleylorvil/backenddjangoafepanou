# views.py
import logging
from decimal import Decimal
from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .serializers import (
    CreatePaymentSerializer, PaymentTransactionSerializer, 
    PaymentStatusSerializer, OrderSerializer, CustomerStatusSerializer,
    PayoutSerializer, RefundSerializer, BalanceSerializer
)
from .models import PaymentTransaction, Order, PaymentNotification
from .services import MonCashService, MonCashAPIError

# Configuration du logger
logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Récupère l'adresse IP du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Récupère le User-Agent du client"""
    return request.META.get('HTTP_USER_AGENT', '')


def setup_moncash_service(request):
    """Configure le service MonCash avec le contexte de la requête"""
    service = MonCashService()
    service.set_request_context(
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )
    return service


# =================== PAIEMENTS ENTRANTS ===================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_payment(request):
    """
    Crée un nouveau paiement MonCash
    
    Body:
    {
        "order_id": 123,
        "amount": 1500.00,  // optionnel
        "return_url": "https://monsite.com/success"  // optionnel
    }
    """
    serializer = CreatePaymentSerializer(data=request.data)
    if not serializer.is_valid():
        logger.warning(f"Données invalides pour create_payment: {serializer.errors}")
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        order = get_object_or_404(Order, id=serializer.validated_data['order_id'])
        
        # Vérifier que l'utilisateur peut payer cette commande
        if order.customer != request.user:
            logger.warning(f"Tentative de paiement non autorisée par {request.user.id} pour commande {order.id}")
            return Response({
                'success': False,
                'error': 'Vous n\'êtes pas autorisé à payer cette commande'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier qu'il n'y a pas déjà un paiement en cours
        existing_payment = PaymentTransaction.objects.filter(
            order=order,
            status__in=['initiated', 'pending', 'processing']
        ).first()
        
        if existing_payment and not existing_payment.is_expired:
            return Response({
                'success': False,
                'error': 'Un paiement est déjà en cours pour cette commande',
                'existing_transaction': PaymentTransactionSerializer(existing_payment).data
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le paiement
        moncash_service = setup_moncash_service(request)
        result = moncash_service.create_payment(
            order_id=order.id,
            amount=serializer.validated_data.get('amount'),
            return_url=serializer.validated_data.get('return_url')
        )
        
        if result['success']:
            transaction_serializer = PaymentTransactionSerializer(result['transaction'])
            logger.info(f"Paiement créé avec succès pour utilisateur {request.user.id}, transaction {result['transaction'].id}")
            
            return Response({
                'success': True,
                'message': 'Paiement créé avec succès',
                'transaction': transaction_serializer.data,
                'payment_url': result['payment_url'],
                'expires_at': result['expires_at']
            }, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Échec de création de paiement: {result['error']}")
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except MonCashAPIError as e:
        logger.error(f"Erreur API MonCash: {str(e)}")
        return Response({
            'success': False,
            'error': f'Erreur MonCash: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la création de paiement: {str(e)}")
        return Response({
            'success': False,
            'error': 'Une erreur inattendue s\'est produite'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_payment_status(request):
    """
    Vérifie le statut d'un paiement
    
    Body:
    {
        "transaction_id": "12345",  // ou
        "external_order_id": "ORD-ABC123"
    }
    """
    serializer = PaymentStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Trouver la transaction
        transaction = None
        if serializer.validated_data.get('transaction_id'):
            transaction = get_object_or_404(
                PaymentTransaction, 
                transaction_id=serializer.validated_data['transaction_id']
            )
        elif serializer.validated_data.get('external_order_id'):
            transaction = get_object_or_404(
                PaymentTransaction, 
                external_order_id=serializer.validated_data['external_order_id']
            )
        
        # Vérifier les permissions
        if transaction.order and transaction.order.customer != request.user and not request.user.is_staff:
            return Response({
                'success': False,
                'error': 'Vous n\'êtes pas autorisé à consulter cette transaction'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Mettre à jour le statut via l'API MonCash
        moncash_service = setup_moncash_service(request)
        updated = moncash_service.update_transaction_status(transaction)
        
        transaction.refresh_from_db()
        transaction_serializer = PaymentTransactionSerializer(transaction)
        
        logger.info(f"Statut vérifié pour transaction {transaction.id}, mis à jour: {updated}")
        
        return Response({
            'success': True,
            'updated': updated,
            'transaction': transaction_serializer.data
        })
        
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du statut: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):
    """
    Récupère l'historique des paiements de l'utilisateur
    
    Query params:
    - page_size: nombre d'éléments par page (max 100)
    - page: numéro de page
    - status: filtrer par statut
    - payment_type: filtrer par type
    """
    # Paramètres de pagination
    page_size = min(int(request.GET.get('page_size', 20)), 100)
    page = int(request.GET.get('page', 1))
    
    # Filtres
    queryset = PaymentTransaction.objects.filter(
        order__customer=request.user
    ).select_related('order').order_by('-created_at')
    
    # Filtrer par statut
    status_filter = request.GET.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Filtrer par type
    type_filter = request.GET.get('payment_type')
    if type_filter:
        queryset = queryset.filter(payment_type=type_filter)
    
    # Pagination
    paginator = Paginator(queryset, page_size)
    try:
        transactions_page = paginator.page(page)
    except:
        transactions_page = paginator.page(1)
    
    serializer = PaymentTransactionSerializer(transactions_page.object_list, many=True)
    
    return Response({
        'success': True,
        'transactions': serializer.data,
        'pagination': {
            'current_page': transactions_page.number,
            'total_pages': paginator.num_pages,
            'total_items': paginator.count,
            'has_next': transactions_page.has_next(),
            'has_previous': transactions_page.has_previous()
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_detail(request, transaction_id):
    """
    Récupère les détails d'une transaction spécifique
    """
    try:
        transaction = get_object_or_404(
            PaymentTransaction.objects.select_related('order'),
            id=transaction_id
        )
        
        # Vérifier les permissions
        if (transaction.order and transaction.order.customer != request.user and 
            not request.user.is_staff):
            return Response({
                'success': False,
                'error': 'Vous n\'êtes pas autorisé à consulter cette transaction'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = PaymentTransactionSerializer(transaction)
        return Response({
            'success': True,
            'transaction': serializer.data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =================== GESTION DES CLIENTS ===================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_customer_status(request):
    """
    Vérifie le statut KYC d'un client MonCash
    
    Body:
    {
        "account": "50912345678"
    }
    """
    serializer = CustomerStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        moncash_service = setup_moncash_service(request)
        result = moncash_service.check_customer_status(
            account=serializer.validated_data['account']
        )
        
        logger.info(f"Statut client vérifié: {serializer.validated_data['account']}")
        return Response(result)
        
    except MonCashAPIError as e:
        logger.error(f"Erreur API lors de la vérification client: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =================== PAYOUTS (ADMIN ONLY) ===================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_payout(request):
    """
    Crée un payout (paiement sortant) - ADMIN ONLY
    
    Body:
    {
        "receiver": "50912345678",
        "amount": 500.00,
        "description": "Paiement fournisseur",
        "reference": "PAY-001"  // optionnel
    }
    """
    serializer = PayoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        moncash_service = setup_moncash_service(request)
        result = moncash_service.create_payout(
            receiver=serializer.validated_data['receiver'],
            amount=serializer.validated_data['amount'],
            description=serializer.validated_data['description'],
            reference=serializer.validated_data.get('reference')
        )
        
        if result['success']:
            transaction_serializer = PaymentTransactionSerializer(result['transaction'])
            logger.info(f"Payout créé par admin {request.user.id}: {result['transaction'].id}")
            
            return Response({
                'success': True,
                'message': 'Payout créé avec succès',
                'transaction': transaction_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except MonCashAPIError as e:
        logger.error(f"Erreur API lors du payout: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def check_payout_status(request):
    """
    Vérifie le statut d'un payout via sa référence
    
    Body:
    {
        "reference": "PAYOUT-ABC123"
    }
    """
    reference = request.data.get('reference')
    if not reference:
        return Response({
            'success': False,
            'error': 'Référence requise'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        moncash_service = setup_moncash_service(request)
        result = moncash_service.check_payout_status(reference)
        
        logger.info(f"Statut payout vérifié: {reference}")
        return Response({
            'success': True,
            'status_data': result
        })
        
    except MonCashAPIError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =================== REMBOURSEMENTS ===================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_refund(request):
    """
    Crée un remboursement pour une transaction
    
    Body:
    {
        "transaction_id": 456,
        "amount": 750.00,  // optionnel, montant total si non spécifié
        "reason": "Produit défectueux"
    }
    """
    serializer = RefundSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Récupérer la transaction originale
        original_transaction = get_object_or_404(
            PaymentTransaction, 
            id=serializer.validated_data['transaction_id']
        )
        
        # Vérifier les permissions (propriétaire de la commande ou admin)
        if (not request.user.is_staff and 
            original_transaction.order.customer != request.user):
            return Response({
                'success': False,
                'error': 'Vous n\'êtes pas autorisé à rembourser cette transaction'
            }, status=status.HTTP_403_FORBIDDEN)
        
        moncash_service = setup_moncash_service(request)
        result = moncash_service.create_refund(
            original_transaction_id=serializer.validated_data['transaction_id'],
            amount=serializer.validated_data.get('amount'),
            reason=serializer.validated_data.get('reason')
        )
        
        if result['success']:
            refund_serializer = PaymentTransactionSerializer(result['transaction'])
            logger.info(f"Remboursement créé: {result['transaction'].id}")
            
            return Response({
                'success': True,
                'message': 'Remboursement traité avec succès',
                'refund_transaction': refund_serializer.data,
                'original_transaction_id': result['original_transaction'].id,
                'refund_amount': result['refund_amount'],
                'remaining_amount': result['remaining_amount']
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': 'Échec du remboursement'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except MonCashAPIError as e:
        logger.error(f"Erreur API lors du remboursement: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =================== FINANCES (ADMIN ONLY) ===================

@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_balance(request):
    """
    Récupère le solde du compte préfinancé - ADMIN ONLY
    """
    try:
        moncash_service = setup_moncash_service(request)
        result = moncash_service.get_balance()
        
        if result['success']:
            logger.info(f"Solde consulté par admin {request.user.id}")
            return Response({
                'success': True,
                'balance': result['balance'],
                'currency': result['currency'],
                'last_updated': result['last_updated']
            })
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except MonCashAPIError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def payment_analytics(request):
    """
    Statistiques et analytics des paiements - ADMIN ONLY
    
    Query params:
    - days: nombre de jours (défaut: 30)
    - detailed: inclure les détails par jour (true/false)
    """
    try:
        # Période
        days = int(request.GET.get('days', 30))
        detailed = request.GET.get('detailed', 'false').lower() == 'true'
        start_date = timezone.now() - timedelta(days=days)
        
        # Statistiques globales
        transactions = PaymentTransaction.objects.filter(created_at__gte=start_date)
        
        # Calculs de base
        total_transactions = transactions.count()
        successful_payments = transactions.filter(status='success', payment_type='payment').count()
        failed_payments = transactions.filter(status='failed', payment_type='payment').count()
        
        # Montants
        revenue = transactions.filter(
            status='success', payment_type='payment'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        payouts_amount = transactions.filter(
            status='success', payment_type='payout'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        refunds_amount = transactions.filter(
            status='success', payment_type='refund'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Moyennes
        avg_payment = transactions.filter(
            status='success', payment_type='payment'
        ).aggregate(avg=Avg('amount'))['avg'] or Decimal('0')
        
        # Taux de succès
        total_payment_attempts = transactions.filter(payment_type='payment').count()
        success_rate = (successful_payments / total_payment_attempts * 100) if total_payment_attempts > 0 else 0
        
        stats = {
            'period_days': days,
            'total_transactions': total_transactions,
            'successful_payments': successful_payments,
            'failed_payments': failed_payments,
            'total_payouts': transactions.filter(payment_type='payout').count(),
            'total_refunds': transactions.filter(payment_type='refund').count(),
            'total_revenue': float(revenue),
            'total_payouts_amount': float(payouts_amount),
            'total_refunds_amount': float(refunds_amount),
            'average_payment': float(avg_payment),
            'success_rate': round(success_rate, 2),
            'net_income': float(revenue - payouts_amount - refunds_amount)
        }
        
        response_data = {
            'success': True,
            'statistics': stats
        }
        
        # Ajouter les détails par jour si demandé
        if detailed:
            daily_stats = []
            for i in range(days):
                day = timezone.now().date() - timedelta(days=i)
                day_transactions = transactions.filter(created_at__date=day)
                
                daily_revenue = day_transactions.filter(
                    status='success', payment_type='payment'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                daily_stats.append({
                    'date': day.isoformat(),
                    'total_transactions': day_transactions.count(),
                    'successful_payments': day_transactions.filter(
                        status='success', payment_type='payment'
                    ).count(),
                    'failed_payments': day_transactions.filter(
                        status='failed', payment_type='payment'
                    ).count(),
                    'revenue': float(daily_revenue),
                    'refunds': day_transactions.filter(payment_type='refund').count()
                })
            
            response_data['daily_breakdown'] = list(reversed(daily_stats))
        
        logger.info(f"Analytics consultées par admin {request.user.id}")
        return Response(response_data)
        
    except Exception as e:
        logger.error(f"Erreur lors du calcul des analytics: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =================== WEBHOOKS ===================

@csrf_exempt
@api_view(['POST'])
def payment_webhook(request):
    """
    Endpoint pour recevoir les notifications de MonCash (webhook)
    
    Note: Cet endpoint ne nécessite pas d'authentification car il est appelé par MonCash
    """
    try:
        # Log de la réception du webhook
        logger.info(f"Webhook reçu depuis IP: {get_client_ip(request)}")
        
        # Enregistrer la notification
        notification = PaymentNotification.objects.create(
            raw_data=request.data,
            received_at=timezone.now()
        )
        
        # Traiter la notification
        if 'orderId' in request.data or 'transactionId' in request.data:
            try:
                # Trouver la transaction correspondante
                transaction = None
                if 'orderId' in request.data:
                    transaction = PaymentTransaction.objects.filter(
                        external_order_id=request.data['orderId']
                    ).first()
                elif 'transactionId' in request.data:
                    transaction = PaymentTransaction.objects.filter(
                        transaction_id=request.data['transactionId']
                    ).first()
                
                if transaction:
                    notification.transaction = transaction
                    
                    # Mettre à jour le statut de la transaction
                    moncash_service = MonCashService()
                    updated = moncash_service.update_transaction_status(transaction)
                    
                    notification.processed = True
                    notification.save()
                    
                    logger.info(f"Webhook traité pour transaction {transaction.id}, mis à jour: {updated}")
                else:
                    logger.warning(f"Transaction non trouvée pour webhook: {request.data}")
                
            except Exception as e:
                notification.processing_error = str(e)
                notification.save()
                logger.error(f"Erreur lors du traitement du webhook: {str(e)}")
        
        return Response({'success': True}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erreur lors de la réception du webhook: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =================== UTILITAIRES ===================

@api_view(['POST'])
@permission_classes([IsAdminUser])
def cleanup_expired_transactions(request):
    """
    Nettoie les transactions expirées - ADMIN ONLY
    """
    try:
        moncash_service = setup_moncash_service(request)
        count = moncash_service.cleanup_expired_transactions()
        
        logger.info(f"Nettoyage effectué par admin {request.user.id}: {count} transactions")
        return Response({
            'success': True,
            'message': f'{count} transactions expirées ont été nettoyées'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_summary(request):
    """
    Résumé des paiements pour l'utilisateur connecté
    """
    try:
        user_transactions = PaymentTransaction.objects.filter(
            order__customer=request.user
        )
        
        summary = {
            'total_transactions': user_transactions.count(),
            'successful_payments': user_transactions.filter(
                status='success', payment_type='payment'
            ).count(),
            'pending_payments': user_transactions.filter(
                status__in=['initiated', 'pending', 'processing']
            ).count(),
            'total_spent': float(user_transactions.filter(
                status='success', payment_type='payment'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')),
            'total_refunded': float(user_transactions.filter(
                status='success', payment_type='refund'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0'))
        }
        
        return Response({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)