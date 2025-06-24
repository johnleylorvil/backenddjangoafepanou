#!/usr/bin/env python
"""
Script pour générer des données de test pour l'application Django
À lancer depuis le répertoire racine du projet (où se trouve manage.py)

Usage: python generate_test_data.py
"""

import os
import sys
import django
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'afepanou.settings')  # Remplacez par votre module settings
django.setup()

# Imports des modèles après setup Django
from django.contrib.auth.models import User
from marketplace.models import (  # Remplacez 'stores' par le nom de votre app
    Store, ProductCategory, ProductTag, Product, 
    ProductImage, Address, Order, OrderItem
)

class DataGenerator:
    def __init__(self):
        self.users = []
        self.stores = []
        self.categories = []
        self.tags = []
        self.products = []
        self.addresses = []
        self.orders = []
        
        # Données de test
        self.store_names = [
            'Boutique Élégance', 'TechShop Haiti', 'Mode Créole', 
            'Artisanat Local', 'Épicerie Moderne', 'Formation Plus',
            'Services Pro', 'Beauté Tropicale', 'Librairie Soleil',
            'Électronique Caraïbe'
        ]
        
        self.category_data = [
            ('Électronique', 'Produits électroniques et high-tech'),
            ('Vêtements', 'Mode et accessoires'),
            ('Alimentation', 'Produits alimentaires'),
            ('Beauté', 'Cosmétiques et soins'),
            ('Maison', 'Articles pour la maison'),
            ('Formation', 'Cours et formations'),
            ('Services', 'Services professionnels'),
            ('Artisanat', 'Produits artisanaux locaux'),
            ('Livres', 'Livres et publications'),
            ('Sport', 'Articles de sport'),
        ]
        
        self.subcategory_data = {
            'Électronique': ['Smartphones', 'Ordinateurs', 'Accessoires'],
            'Vêtements': ['Homme', 'Femme', 'Enfant', 'Chaussures'],
            'Alimentation': ['Fruits', 'Légumes', 'Épices', 'Boissons'],
            'Beauté': ['Soins visage', 'Maquillage', 'Parfums'],
            'Maison': ['Décoration', 'Cuisine', 'Jardin'],
        }
        
        self.tag_names = [
            'Nouveau', 'Populaire', 'Promo', 'Local', 'Bio', 
            'Handmade', 'Premium', 'Éco-friendly', 'Tendance', 'Unique'
        ]
        
        self.product_names = {
            'physical': [
                'iPhone 14 Pro', 'MacBook Air', 'Robe créole traditionnelle',
                'Café haïtien premium', 'Masque à l\'argile', 'Sculpture en bois',
                'Livre d\'histoire d\'Haïti', 'Chaussures en cuir', 'Épices locales',
                'Sac à main artisanal', 'Bijoux créoles', 'Peinture locale'
            ],
            'service': [
                'Consultation marketing', 'Service de livraison', 'Réparation électronique',
                'Coiffure à domicile', 'Nettoyage professionnel', 'Traduction',
                'Service comptable', 'Consultation juridique'
            ],
            'training': [
                'Formation en informatique', 'Cours de créole', 'Atelier de cuisine',
                'Formation entrepreneuriat', 'Cours de français', 'Atelier artisanat',
                'Formation marketing digital', 'Cours de musique'
            ]
        }
        
        self.haitian_cities = [
            'Port-au-Prince', 'Cap-Haïtien', 'Gonaïves', 'Les Cayes',
            'Jacmel', 'Jérémie', 'Fort-Liberté', 'Hinche', 'Petit-Goâve',
            'Saint-Marc', 'Léogâne', 'Croix-des-Bouquets'
        ]
        
        self.haitian_departments = [
            'Ouest', 'Nord', 'Artibonite', 'Sud', 'Sud-Est',
            'Grande-Anse', 'Nord-Est', 'Centre', 'Nippes', 'Nord-Ouest'
        ]

    def generate_users(self, count=20):
        """Génère des utilisateurs"""
        print(f"Génération de {count} utilisateurs...")
        
        first_names = ['Jean', 'Marie', 'Pierre', 'Anne', 'Jacques', 'Claudette', 
                      'Michel', 'Rose', 'Paul', 'Joséphine', 'François', 'Micheline']
        last_names = ['Dupont', 'Martin', 'Bernard', 'Durand', 'Moreau', 'Simon',
                     'Laurent', 'Lefebvre', 'Roux', 'Fournier', 'Girard', 'Bonnet']
        
        for i in range(count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}.{last_name.lower()}{i}"
            email = f"{username}@example.com"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                last_name=last_name
            )
            self.users.append(user)
        
        print(f"✓ {count} utilisateurs créés")

    def generate_stores(self, count=10):
        """Génère des boutiques"""
        print(f"Génération de {count} boutiques...")
        
        for i in range(min(count, len(self.store_names))):
            store_name = self.store_names[i]
            owner = random.choice(self.users)
            
            store = Store.objects.create(
                name=store_name,
                owner=owner,
                description=f"<p>Description de la boutique {store_name}. Nous offrons des produits de qualité avec un service client exceptionnel.</p>",
                is_active=True
            )
            self.stores.append(store)
        
        print(f"✓ {len(self.stores)} boutiques créées")

    def generate_categories(self):
        """Génère des catégories de produits"""
        print("Génération des catégories...")
        
        # Catégories principales
        for name, description in self.category_data:
            category = ProductCategory.objects.create(
                name=name,
                description=description
            )
            self.categories.append(category)
        
        # Sous-catégories
        for parent_name, subcats in self.subcategory_data.items():
            try:
                parent = ProductCategory.objects.get(name=parent_name)
                for subcat_name in subcats:
                    subcat = ProductCategory.objects.create(
                        name=subcat_name,
                        description=f"Sous-catégorie de {parent_name}",
                        parent=parent
                    )
                    self.categories.append(subcat)
            except ProductCategory.DoesNotExist:
                continue
        
        print(f"✓ {len(self.categories)} catégories créées")

    def generate_tags(self):
        """Génère des tags"""
        print("Génération des tags...")
        
        for tag_name in self.tag_names:
            tag = ProductTag.objects.create(name=tag_name)
            self.tags.append(tag)
        
        print(f"✓ {len(self.tags)} tags créés")

    def generate_products(self, count=50):
        """Génère des produits"""
        print(f"Génération de {count} produits...")
        
        product_types = ['physical', 'service', 'training']
        currencies = ['HTG', 'USD']
        statuses = ['available', 'out_of_stock', 'discontinued']
        
        for i in range(count):
            product_type = random.choice(product_types)
            product_names = self.product_names[product_type]
            
            if not product_names:
                continue
                
            name = random.choice(product_names)
            store = random.choice(self.stores)
            
            # Prix basé sur le type de produit
            if product_type == 'physical':
                price = Decimal(str(random.uniform(10, 1000)))
                stock_quantity = random.randint(0, 100) if random.random() > 0.1 else 0
            elif product_type == 'service':
                price = Decimal(str(random.uniform(50, 500)))
                stock_quantity = None
            else:  # training
                price = Decimal(str(random.uniform(100, 2000)))
                stock_quantity = random.randint(1, 20)
            
            # Statut basé sur le stock
            if stock_quantity == 0:
                status = 'out_of_stock'
            elif random.random() > 0.95:
                status = 'discontinued'
            else:
                status = 'available'
            
            product = Product.objects.create(
                name=f"{name} #{i+1}",
                store=store,
                product_type=product_type,
                description=f"<p>Description détaillée du produit {name}. Excellent produit de qualité supérieure.</p>",
                price=price,
                currency=random.choice(currencies),
                status=status,
                stock_quantity=stock_quantity,
                duration=f"{random.randint(1, 10)} heures" if product_type in ['service', 'training'] else "",
                format="En ligne" if product_type == 'training' else ""
            )
            
            # Associer des catégories (1-3 par produit)
            categories_to_add = random.sample(self.categories, random.randint(1, min(3, len(self.categories))))
            product.categories.set(categories_to_add)
            
            # Associer des tags (0-4 par produit)
            tags_to_add = random.sample(self.tags, random.randint(0, min(4, len(self.tags))))
            product.tags.set(tags_to_add)
            
            self.products.append(product)
        
        print(f"✓ {len(self.products)} produits créés")

    def generate_addresses(self, count=30):
        """Génère des adresses"""
        print(f"Génération de {count} adresses...")
        
        for i in range(count):
            user = random.choice(self.users)
            city = random.choice(self.haitian_cities)
            department = random.choice(self.haitian_departments)
            
            address = Address.objects.create(
                user=user,
                name=f"{user.first_name} {user.last_name}",
                address_line1=f"{random.randint(1, 999)} Rue {random.randint(1, 50)}",
                address_line2=f"Apt {random.randint(1, 20)}" if random.random() > 0.7 else "",
                city=city,
                state=department,
                phone=f"+509 {random.randint(10000000, 99999999)}",
                is_default=random.random() > 0.7
            )
            self.addresses.append(address)
        
        print(f"✓ {len(self.addresses)} adresses créées")

    def generate_orders(self, count=25):
        """Génère des commandes"""
        print(f"Génération de {count} commandes...")
        
        statuses = ['pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled']
        
        for i in range(count):
            customer = random.choice(self.users)
            customer_addresses = [addr for addr in self.addresses if addr.user == customer]
            
            if not customer_addresses:
                # Créer une adresse pour ce client
                address = Address.objects.create(
                    user=customer,
                    name=f"{customer.first_name} {customer.last_name}",
                    address_line1=f"{random.randint(1, 999)} Rue principale",
                    city=random.choice(self.haitian_cities),
                    state=random.choice(self.haitian_departments),
                    phone=f"+509 {random.randint(10000000, 99999999)}",
                    is_default=True
                )
                customer_addresses = [address]
            
            shipping_address = random.choice(customer_addresses)
            
            order = Order.objects.create(
                customer=customer,
                order_number=f"ORD-{datetime.now().year}-{str(i+1).zfill(4)}",
                status=random.choice(statuses),
                shipping_address=shipping_address,
                total_amount=Decimal('0'),  # Sera calculé après ajout des items
                shipping_cost=Decimal(str(random.uniform(5, 50))),
                notes=f"Commande #{i+1} - Notes spéciales" if random.random() > 0.7 else ""
            )
            
            # Ajouter des items à la commande (1-5 produits)
            available_products = [p for p in self.products if p.status == 'available']
            if available_products:
                num_items = random.randint(1, min(5, len(available_products)))
                selected_products = random.sample(available_products, num_items)
                
                total_amount = Decimal('0')
                
                for product in selected_products:
                    quantity = random.randint(1, 3)
                    price = product.price
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=price
                    )
                    
                    total_amount += price * quantity
                
                # Mettre à jour le montant total
                order.total_amount = total_amount + order.shipping_cost
                order.save()
            
            self.orders.append(order)
        
        print(f"✓ {len(self.orders)} commandes créées")

    def run(self):
        """Exécute la génération complète des données"""
        print("🚀 Début de la génération des données de test...")
        print("-" * 50)
        
        try:
            # Générer dans l'ordre des dépendances
            self.generate_users(20)
            self.generate_stores(10)
            self.generate_categories()
            self.generate_tags()
            self.generate_products(50)
            self.generate_addresses(30)
            self.generate_orders(25)
            
            print("-" * 50)
            print("✅ Génération terminée avec succès!")
            print(f"📊 Résumé:")
            print(f"   - Utilisateurs: {len(self.users)}")
            print(f"   - Boutiques: {len(self.stores)}")
            print(f"   - Catégories: {len(self.categories)}")
            print(f"   - Tags: {len(self.tags)}")
            print(f"   - Produits: {len(self.products)}")
            print(f"   - Adresses: {len(self.addresses)}")
            print(f"   - Commandes: {len(self.orders)}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la génération: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    generator = DataGenerator()
    generator.run()