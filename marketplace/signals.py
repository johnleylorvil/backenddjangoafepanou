# marketplace/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Cart, Product, ProductImage, Order

@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """
    Crée automatiquement un panier pour chaque nouvel utilisateur.
    """
    if created:
        Cart.objects.create(user=instance)

@receiver(post_save, sender=ProductImage)
def set_default_main_image(sender, instance, created, **kwargs):
    """
    Si c'est la première image d'un produit, la définir comme image principale.
    """
    if created:
        # Si c'est la première image, la définir comme principale
        if instance.product.images.count() == 1:
            instance.is_main = True
            instance.save()

@receiver(post_save, sender=Order)
def update_product_stock(sender, instance, created, **kwargs):
    """
    Met à jour le stock des produits après une commande.
    """
    if created:
        # Pour chaque article de la commande
        for item in instance.items.all():
            # Si c'est un produit physique avec un stock
            if item.product.product_type == 'physical' and item.product.stock_quantity is not None:
                # Décrémenter le stock
                item.product.stock_quantity -= item.quantity
                # Si le stock atteint zéro, mettre le statut à 'rupture de stock'
                if item.product.stock_quantity <= 0:
                    item.product.status = 'out_of_stock'
                item.product.save()