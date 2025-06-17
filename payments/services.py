# payments/services.py
import requests
import json
import logging
from django.conf import settings
from django.urls import reverse
from .models import PaymentTransaction

logger = logging.getLogger(__name__)

class MonCashService:
    """
    Service pour gérer l'intégration avec l'API MonCash.
    """
    def __init__(self):
        self.client_id = settings.MONCASH_CLIENT_ID
        self.client_secret = settings.MONCASH_CLIENT_SECRET
        self.api_host = settings.MONCASH_API_HOST
        self.gateway_url = settings.MONCASH_GATEWAY_URL
        self.mode = settings.MONCASH_MODE
        self.return_url = settings.MONCASH_RETURN_URL
        self.cancel_url = settings.MONCASH_CANCEL_URL
        self.access_token = None
    
    def get_auth_token(self):
        """
        Obtient un token d'authentification OAuth 2.0 de MonCash.
        """
        url = f"https://{self.api_host}/oauth/token"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        auth = (self.client_id, self.client_secret)
        data = "scope=read,write&grant_type=client_credentials"
        
        try:
            response = requests.post(url, auth=auth, headers=headers, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            
            return self.access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de l'obtention du token MonCash: {str(e)}")
            raise
    
    def create_payment(self, order_id, amount):
        """
        Crée une demande de paiement MonCash.
        """
        if not self.access_token:
            self.get_auth_token()
        
        url = f"https://{self.api_host}/v1/CreatePayment"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        payload = {
            "amount": str(amount),
            "orderId": order_id
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            payment_data = response.json()
            payment_token = payment_data.get('payment_token', {}).get('token')
            
            # Construire l'URL de redirection vers la passerelle de paiement
            payment_url = f"{self.gateway_url}/Payment/Redirect?token={payment_token}"
            
            return {
                'payment_token': payment_token,
                'payment_url': payment_url,
                'response': payment_data
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la création du paiement MonCash: {str(e)}")
            raise
    
    def check_payment_by_transaction_id(self, transaction_id):
        """
        Vérifie le statut d'un paiement par ID de transaction.
        """
        if not self.access_token:
            self.get_auth_token()
        
        url = f"https://{self.api_host}/v1/RetrieveTransactionPayment"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        payload = {
            "transactionId": transaction_id
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la vérification du paiement par transaction_id: {str(e)}")
            raise
    
    def check_payment_by_order_id(self, order_id):
        """
        Vérifie le statut d'un paiement par ID de commande.
        """
        if not self.access_token:
            self.get_auth_token()
        
        url = f"https://{self.api_host}/v1/RetrieveOrderPayment"
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }
        
        payload = {
            "orderId": order_id
        }
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la vérification du paiement par order_id: {str(e)}")
            raise