from django.urls import path, include
from . import views

app_name = 'payments'

urlpatterns = [
    # =================== PAIEMENTS ENTRANTS ===================
    path('create/', views.create_payment, name='create_payment'),
    path('status/', views.check_payment_status, name='check_payment_status'),
    path('history/', views.payment_history, name='payment_history'),
    path('transaction/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
    path('summary/', views.payment_summary, name='payment_summary'),
    
    # =================== GESTION DES CLIENTS ===================
    path('customer/status/', views.check_customer_status, name='check_customer_status'),
    
    # =================== PAYOUTS (ADMIN ONLY) ===================
    path('payout/create/', views.create_payout, name='create_payout'),
    path('payout/status/', views.check_payout_status, name='check_payout_status'),
    
    # =================== REMBOURSEMENTS ===================
    path('refund/create/', views.create_refund, name='create_refund'),
    
    # =================== FINANCES (ADMIN ONLY) ===================
    path('balance/', views.get_balance, name='get_balance'),
    path('analytics/', views.payment_analytics, name='payment_analytics'),
    
    # =================== WEBHOOKS ET UTILITAIRES ===================
    path('webhook/', views.payment_webhook, name='payment_webhook'),
    path('cleanup/', views.cleanup_expired_transactions, name='cleanup_expired_transactions'),
]

