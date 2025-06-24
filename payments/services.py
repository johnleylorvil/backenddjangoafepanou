# services.py
import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
from .models import PaymentTransaction
from marketplace.models import Order
import uuid

# Configuration du logger
logger = logging.getLogger(__name__)


class MonCashAPIError(Exception):
    """Exception personnalisée pour les erreurs API MonCash"""
    pass


class MonCashService:
    """Service pour interagir avec l'API MonCash de Digicel"""
    
    def __init__(self):
        self.client_id = getattr(settings, 'MONCASH_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'MONCASH_CLIENT_SECRET', '')
        self.base_url = getattr(settings, 'MONCASH_API_BASE_URL', '')
        self.gateway_url = getattr(settings, 'MONCASH_GATEWAY_BASE_URL', '')
        self.mode = getattr(settings, 'MONCASH_MODE', 'sandbox')
        self.timeout = getattr(settings, 'MONCASH_TIMEOUT', 30)
        
        # Validation de la configuration
        if not all([self.client_id, self.client_secret, self.base_url]):
            raise MonCashAPIError("Configuration MonCash incomplète. Vérifiez vos settings.")
    
    def _get_cache_key(self, key_type):
        """Génère une clé de cache unique"""
        return f"moncash_{self.mode}_{key_type}"
    
    def get_access_token(self):
        """Obtient un token d'accès OAuth avec mise en cache"""
        cache_key = self._get_cache_key("access_token")
        token = cache.get(cache_key)
        
        if token:
            logger.debug("Token d'accès récupéré depuis le cache")
            return token
        
        url = f"{self.base_url}/oauth/token"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'client_credentials',
            'scope': 'read,write'
        }
        
        try:
            logger.info("Demande d'un nouveau token d'accès MonCash")
            response = requests.post(
                url, 
                headers=headers, 
                data=data,
                auth=(self.client_id, self.client_secret),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 59)
            
            if not access_token:
                raise MonCashAPIError("Token d'accès non reçu")
            
            # Mettre en cache le token (expire 10 secondes avant l'expiration réelle)
            cache_timeout = max(expires_in - 10, 30)
            cache.set(cache_key, access_token, cache_timeout)
            
            logger.info(f"Nouveau token d'accès obtenu, expire dans {expires_in}s")
            return access_token
            
        except requests.RequestException as e:
            logger.error(f"Erreur lors de l'obtention du token: {str(e)}")
            raise MonCashAPIError(f"Erreur d'authentification MonCash: {str(e)}")
    
    def _make_request(self, method, endpoint, data=None, use_auth=True):
        """Méthode générique pour faire des requêtes à l'API MonCash"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Accept': 'application/json'}
        
        if use_auth:
            token = self.get_access_token()
            headers['Authorization'] = f'Bearer {token}'
        
        if data:
            headers['Content-Type'] = 'application/json'
        
        try:
            logger.debug(f"Requête {method} vers {endpoint}")
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=self.timeout)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"Réponse reçue: {response.status_code}")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Erreur de requête API: {str(e)}")
            raise MonCashAPIError(f"Erreur de communication avec MonCash: {str(e)}")
    
    def create_payment(self, order_id, amount=None, return_url=None):
        """Crée un paiement MonCash"""
        try:
            # Récupérer la commande
            order = Order.objects.get(id=order_id)
            if not amount:
                amount = order.total_amount
            
            # Vérifier que la commande n'est pas déjà payée
            if order.status == 'paid':
                raise MonCashAPIError("Cette commande est déjà payée")
            
            # Créer la transaction locale
            transaction = PaymentTransaction.objects.create(
                order=order,
                amount=amount,
                currency='HTG',
                status='initiated',
                payment_type='payment',
                return_url=return_url or '',
                ip_address=getattr(self, '_current_ip', None),
                user_agent=getattr(self, '_current_user_agent', '')
            )
            
            logger.info(f"Transaction créée: {transaction.external_order_id}")
            
            # Préparer les données pour l'API
            api_data = {
                'amount': float(amount),
                'orderId': transaction.external_order_id
            }
            
            # Appel à l'API MonCash
            result = self._make_request('POST', '/v1/CreatePayment', api_data)
            
            # Traiter la réponse
            if result.get('payment_token'):
                payment_token_data = result['payment_token']
                transaction.payment_token = payment_token_data.get('token', '')
                transaction.status = 'pending'
                transaction.response_code = str(result.get('status', ''))
                transaction.api_response_data = result
                
                # Générer l'URL de redirection
                if transaction.payment_token:
                    transaction.redirect_url = f"{self.gateway_url}/Payment/Redirect?token={transaction.payment_token}"
                
                # Définir la date d'expiration (10 minutes)
                transaction.payment_expires_at = timezone.now() + timezone.timedelta(minutes=10)
                transaction.save()
                
                logger.info(f"Paiement créé avec succès: {transaction.id}")
                
                return {
                    'success': True,
                    'transaction': transaction,
                    'payment_url': transaction.redirect_url,
                    'token': transaction.payment_token,
                    'expires_at': transaction.payment_expires_at
                }
            else:
                transaction.status = 'failed'
                transaction.response_message = json.dumps(result)
                transaction.error_details = "Aucun token de paiement reçu"
                transaction.save()
                
                logger.warning(f"Échec de création du paiement: {transaction.id}")
                
                return {
                    'success': False,
                    'error': 'Aucun token de paiement reçu',
                    'transaction': transaction
                }
                
        except Order.DoesNotExist:
            logger.error(f"Commande non trouvée: {order_id}")
            raise MonCashAPIError("Commande non trouvée")
        except Exception as e:
            if 'transaction' in locals():
                transaction.status = 'failed'
                transaction.error_details = str(e)
                transaction.save()
                logger.error(f"Erreur lors de la création du paiement: {str(e)}")
            raise e
    
    def get_payment_details(self, transaction_id=None, order_id=None):
        """Récupère les détails d'un paiement depuis MonCash"""
        if transaction_id:
            endpoint = '/v1/RetrieveTransactionPayment'
            data = {'transactionId': transaction_id}
        elif order_id:
            endpoint = '/v1/RetrieveOrderPayment'
            data = {'orderId': order_id}
        else:
            raise MonCashAPIError("transaction_id ou order_id requis")
        
        logger.info(f"Récupération des détails de paiement: {transaction_id or order_id}")
        return self._make_request('POST', endpoint, data)
    
    def check_customer_status(self, account):
        """Vérifie le statut KYC d'un client MonCash"""
        logger.info(f"Vérification du statut client: {account}")
        
        data = {'account': account}
        result = self._make_request('POST', '/v1/CustomerStatus', data)
        
        if result.get('customerStatus'):
            customer_status = result['customerStatus']
            return {
                'success': True,
                'status': customer_status.get('status', []),
                'type': customer_status.get('type', ''),
                'account': account,
                'is_active': 'active' in customer_status.get('status', []),
                'is_registered': 'registered' in customer_status.get('status', [])
            }
        else:
            return {
                'success': False,
                'error': 'Compte non trouvé ou inactif',
                'account': account
            }
    
    def create_payout(self, receiver, amount, description, reference=None):
        """Effectue un paiement sortant (payout)"""
        try:
            # Vérifier le statut du destinataire
            logger.info(f"Création d'un payout vers {receiver}: {amount} HTG")
            
            customer_status = self.check_customer_status(receiver)
            if not customer_status['success']:
                raise MonCashAPIError(f"Destinataire invalide: {customer_status.get('error', 'Compte non trouvé')}")
            
            if not customer_status['is_active']:
                raise MonCashAPIError("Le compte destinataire n'est pas actif")
            
            # Générer une référence unique si non fournie
            if not reference:
                reference = f"PAYOUT-{uuid.uuid4().hex[:12].upper()}"
            
            # Créer la transaction locale
            transaction = PaymentTransaction.objects.create(
                order=None,  # Les payouts ne sont pas liés à une commande
                amount=amount,
                currency='HTG',
                status='initiated',
                payment_type='payout',
                reference=reference,
                payer_account=receiver,
                notes=description
            )
            
            # Préparer les données pour l'API
            api_data = {
                'amount': float(amount),
                'receiver': receiver,
                'desc': description,
                'reference': reference
            }
            
            # Appel à l'API MonCash
            result = self._make_request('POST', '/v1/Transfert', api_data)
            
            # Traiter la réponse
            if result.get('transfer'):
                transfer_info = result['transfer']
                
                if transfer_info.get('message') == 'successful':
                    transaction.status = 'success'
                    transaction.payment_completed_at = timezone.now()
                    logger.info(f"Payout réussi: {transaction.id}")
                else:
                    transaction.status = 'failed'
                    logger.warning(f"Payout échoué: {transaction.id}")
                
                transaction.transaction_id = transfer_info.get('transaction_id', '')
                transaction.response_message = transfer_info.get('message', '')
                transaction.api_response_data = result
                transaction.save()
                
                return {
                    'success': transaction.status == 'success',
                    'transaction': transaction,
                    'moncash_transaction_id': transfer_info.get('transaction_id'),
                    'message': transfer_info.get('message', '')
                }
            else:
                transaction.status = 'failed'
                transaction.error_details = "Réponse API invalide"
                transaction.save()
                
                logger.error(f"Réponse API invalide pour payout: {transaction.id}")
                
                return {
                    'success': False,
                    'error': 'Réponse API invalide',
                    'transaction': transaction
                }
                
        except Exception as e:
            if 'transaction' in locals():
                transaction.status = 'failed'
                transaction.error_details = str(e)
                transaction.save()
                logger.error(f"Erreur lors du payout: {str(e)}")
            raise e
    
    def check_payout_status(self, reference):
        """Vérifie le statut d'un payout via sa référence"""
        logger.info(f"Vérification du statut payout: {reference}")
        
        data = {'reference': reference}
        result = self._make_request('POST', '/v1/PrefundedTransactionStatus', data)
        
        # Mettre à jour la transaction locale si elle existe
        try:
            transaction = PaymentTransaction.objects.get(reference=reference)
            
            if result.get('transStatus') == 'successful':
                transaction.status = 'success'
                transaction.payment_completed_at = timezone.now()
                logger.info(f"Payout confirmé comme réussi: {reference}")
            elif result.get('error'):
                transaction.status = 'failed'
                transaction.error_details = result.get('message', '')
                logger.warning(f"Payout confirmé comme échoué: {reference}")
            
            transaction.api_response_data = result
            transaction.save()
            
        except PaymentTransaction.DoesNotExist:
            logger.warning(f"Transaction locale non trouvée pour la référence: {reference}")
        
        return result
    
    def get_balance(self):
        """Récupère le solde du compte préfinancé"""
        logger.info("Récupération du solde du compte préfinancé")
        
        result = self._make_request('GET', '/v1/PrefundedBalance')
        
        if result.get('balance'):
            balance_info = result['balance']
            balance_amount = balance_info.get('balance', 0)
            
            # Nettoyer le montant (MonCash retourne parfois des nombres très précis)
            try:
                balance_decimal = Decimal(str(balance_amount)).quantize(Decimal('0.01'))
            except:
                balance_decimal = Decimal('0.00')
            
            return {
                'success': True,
                'balance': balance_decimal,
                'currency': 'HTG',
                'message': balance_info.get('message', ''),
                'last_updated': timezone.now(),
                'raw_balance': balance_amount
            }
        else:
            return {
                'success': False,
                'error': 'Impossible de récupérer le solde'
            }
    
    def update_transaction_status(self, transaction):
        """Met à jour le statut d'une transaction via l'API MonCash"""
        try:
            logger.info(f"Mise à jour du statut de la transaction: {transaction.id}")
            
            if not transaction.transaction_id and not transaction.external_order_id:
                logger.warning(f"Aucun identifiant pour mettre à jour la transaction: {transaction.id}")
                return False
            
            # Essayer d'abord avec transaction_id puis avec external_order_id
            payment_details = None
            
            if transaction.transaction_id:
                try:
                    payment_details = self.get_payment_details(transaction_id=transaction.transaction_id)
                except MonCashAPIError:
                    logger.debug("Échec de récupération par transaction_id")
            
            if not payment_details and transaction.external_order_id:
                try:
                    payment_details = self.get_payment_details(order_id=transaction.external_order_id)
                except MonCashAPIError:
                    logger.debug("Échec de récupération par external_order_id")
            
            if payment_details and payment_details.get('payment'):
                payment_info = payment_details['payment']
                
                # Mettre à jour le statut selon la réponse
                old_status = transaction.status
                
                if payment_info.get('message') == 'successful':
                    transaction.status = 'success'
                    transaction.payment_completed_at = timezone.now()
                    
                    # Mettre à jour la commande si c'est un paiement entrant
                    if transaction.payment_type == 'payment' and transaction.order:
                        transaction.order.status = 'paid'
                        transaction.order.save()
                        logger.info(f"Commande {transaction.order.order_number} marquée comme payée")
                    
                elif payment_info.get('message') in ['failed', 'cancelled']:
                    transaction.status = 'failed'
                
                # Mettre à jour les détails
                transaction.transaction_id = payment_info.get('transaction_id', transaction.transaction_id)
                transaction.reference = payment_info.get('reference', transaction.reference)
                transaction.payer_phone = payment_info.get('payer', transaction.payer_phone)
                transaction.response_message = payment_info.get('message', '')
                transaction.api_response_data = payment_details
                
                transaction.save()
                
                if old_status != transaction.status:
                    logger.info(f"Statut de transaction mis à jour: {old_status} -> {transaction.status}")
                
                return True
            
            logger.warning(f"Aucun détail de paiement trouvé pour la transaction: {transaction.id}")
            return False
            
        except Exception as e:
            transaction.error_details = str(e)
            transaction.save()
            logger.error(f"Erreur lors de la mise à jour du statut: {str(e)}")
            return False
    
    def create_refund(self, original_transaction_id, amount=None, reason=None):
        """Crée un remboursement pour une transaction"""
        try:
            logger.info(f"Création d'un remboursement pour la transaction: {original_transaction_id}")
            
            # Récupérer la transaction originale
            original_transaction = PaymentTransaction.objects.get(
                id=original_transaction_id, 
                status='success',
                payment_type='payment'
            )
            
            if not amount:
                amount = original_transaction.amount
            elif amount > original_transaction.amount:
                raise MonCashAPIError("Le montant du remboursement ne peut pas dépasser le montant original")
            
            # Vérifier les remboursements existants
            existing_refunds = PaymentTransaction.objects.filter(
                reference=original_transaction.transaction_id,
                payment_type='refund',
                status='success'
            )
            total_refunded = sum(r.amount for r in existing_refunds)
            
            if total_refunded + amount > original_transaction.amount:
                raise MonCashAPIError("Le montant total des remboursements dépasserait le montant original")
            
            # Créer la transaction de remboursement
            refund_transaction = PaymentTransaction.objects.create(
                order=original_transaction.order,
                amount=amount,
                currency='HTG',
                status='initiated',
                payment_type='refund',
                reference=original_transaction.transaction_id,
                payer_account=original_transaction.payer_account or original_transaction.payer_phone,
                notes=f"Remboursement: {reason or 'Aucune raison spécifiée'}"
            )
            
            # Effectuer le remboursement via payout
            if original_transaction.payer_phone:
                description = f"Remboursement commande #{original_transaction.order.order_number}"
                payout_reference = f"REFUND-{refund_transaction.id}"
                
                payout_result = self.create_payout(
                    receiver=original_transaction.payer_phone,
                    amount=amount,
                    description=description,
                    reference=payout_reference
                )
                
                if payout_result['success']:
                    refund_transaction.status = 'success'
                    refund_transaction.payment_completed_at = timezone.now()
                    refund_transaction.transaction_id = payout_result.get('moncash_transaction_id', '')
                    logger.info(f"Remboursement réussi: {refund_transaction.id}")
                else:
                    refund_transaction.status = 'failed'
                    refund_transaction.error_details = payout_result.get('error', '')
                    logger.error(f"Remboursement échoué: {refund_transaction.id}")
                
                refund_transaction.save()
                
                return {
                    'success': payout_result['success'],
                    'transaction': refund_transaction,
                    'original_transaction': original_transaction,
                    'refund_amount': amount,
                    'remaining_amount': original_transaction.amount - total_refunded - amount
                }
            else:
                raise MonCashAPIError("Impossible de rembourser: numéro de téléphone du payeur original non disponible")
                
        except PaymentTransaction.DoesNotExist:
            logger.error(f"Transaction originale non trouvée: {original_transaction_id}")
            raise MonCashAPIError("Transaction originale non trouvée ou non éligible au remboursement")
        except Exception as e:
            if 'refund_transaction' in locals():
                refund_transaction.status = 'failed'
                refund_transaction.error_details = str(e)
                refund_transaction.save()
                logger.error(f"Erreur lors du remboursement: {str(e)}")
            raise e
    
    def set_request_context(self, ip_address=None, user_agent=None):
        """Définit le contexte de la requête pour les logs"""
        self._current_ip = ip_address
        self._current_user_agent = user_agent
    
    def cleanup_expired_transactions(self):
        """Nettoie les transactions expirées"""
        expired_transactions = PaymentTransaction.objects.filter(
            status__in=['initiated', 'pending'],
            payment_expires_at__lt=timezone.now()
        )
        
        count = 0
        for transaction in expired_transactions:
            transaction.mark_as_expired()
            count += 1
        
        logger.info(f"Nettoyage effectué: {count} transactions expirées marquées")
        return count