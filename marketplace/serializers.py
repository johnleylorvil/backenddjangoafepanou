# marketplace/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Store, ProductCategory, ProductTag, Product, ProductImage, 
    Address, Cart, CartItem, Order, OrderItem
)

# Serializers de base
class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

# Store Serializers
class StoreListSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'slug', 'logo', 'owner_name', 'product_count', 'is_active']
    
    def get_owner_name(self, obj):
        return obj.owner.get_full_name() or obj.owner.username
    
    def get_product_count(self, obj):
        return obj.products.count()

class StoreDetailSerializer(serializers.ModelSerializer):
    owner = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Store
        fields = ['id', 'name', 'slug', 'owner', 'description', 'logo', 'banner', 'is_active', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']

class StoreCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['name', 'description', 'logo', 'banner', 'is_active']
    
    def create(self, validated_data):
        # Assigner l'utilisateur courant comme propriétaire
        user = self.context['request'].user
        store = Store.objects.create(owner=user, **validated_data)
        return store

# Product Serializers
class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'slug', 'description', 'parent']
        read_only_fields = ['id', 'slug']

class ProductTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTag
        fields = ['id', 'name', 'slug']
        read_only_fields = ['id', 'slug']

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'is_main', 'caption']
        read_only_fields = ['id']

class ProductListSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_slug = serializers.CharField(source='store.slug', read_only=True)
    main_image = serializers.SerializerMethodField()
    categories = ProductCategorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'store_name', 'store_slug', 
            'price', 'currency', 'status', 'product_type',
            'main_image', 'categories', 'created_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at']
    
    def get_main_image(self, obj):
        main_image = obj.images.filter(is_main=True).first()
        if main_image:
            return self.context['request'].build_absolute_uri(main_image.image.url)
        
        # Retourner la première image si aucune n'est marquée comme principale
        first_image = obj.images.first()
        if first_image:
            return self.context['request'].build_absolute_uri(first_image.image.url)
        
        return None

class ProductDetailSerializer(serializers.ModelSerializer):
    store = StoreListSerializer(read_only=True)
    categories = ProductCategorySerializer(many=True, read_only=True)
    tags = ProductTagSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'store', 'product_type',
            'description', 'price', 'currency', 'status',
            'stock_quantity', 'duration', 'format',
            'categories', 'tags', 'images',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']

class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    store_id = serializers.PrimaryKeyRelatedField(
        source='store',
        queryset=Store.objects.all(),
        write_only=True
    )
    category_ids = serializers.PrimaryKeyRelatedField(
        source='categories',
        queryset=ProductCategory.objects.all(),
        many=True,
        write_only=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        queryset=ProductTag.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Product
        fields = [
            'name', 'store_id', 'product_type', 'description',
            'price', 'currency', 'status', 'stock_quantity',
            'duration', 'format', 'category_ids', 'tag_ids'
        ]
    
    def validate_store_id(self, value):
        # Vérifier que l'utilisateur est propriétaire de la boutique
        user = self.context['request'].user
        if value.owner != user:
            raise serializers.ValidationError("Vous n'êtes pas le propriétaire de cette boutique.")
        return value
    
    def create(self, validated_data):
        categories = validated_data.pop('categories', [])
        tags = validated_data.pop('tags', [])
        
        product = Product.objects.create(**validated_data)
        
        if categories:
            product.categories.set(categories)
        if tags:
            product.tags.set(tags)
        
        return product
    
    def update(self, instance, validated_data):
        categories = validated_data.pop('categories', None)
        tags = validated_data.pop('tags', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if categories is not None:
            instance.categories.set(categories)
        if tags is not None:
            instance.tags.set(tags)
        
        return instance

# Address Serializers
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'name', 'address_line1', 'address_line2',
            'city', 'state', 'phone', 'is_default'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        # Assigner l'utilisateur courant
        user = self.context['request'].user
        address = Address.objects.create(user=user, **validated_data)
        return address

# Cart Serializers
class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        write_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True
    )
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'subtotal', 'added_at']
        read_only_fields = ['id', 'subtotal', 'added_at']
    
    def create(self, validated_data):
        product = validated_data.pop('product_id')
        user = self.context['request'].user
        
        # Obtenir ou créer le panier de l'utilisateur
        cart, created = Cart.objects.get_or_create(user=user)
        
        # Vérifier si le produit est déjà dans le panier
        try:
            cart_item = CartItem.objects.get(cart=cart, product=product)
            # Mettre à jour la quantité
            cart_item.quantity += validated_data.get('quantity', 1)
            cart_item.save()
        except CartItem.DoesNotExist:
            # Créer un nouvel élément de panier
            cart_item = CartItem.objects.create(
                cart=cart,
                product=product,
                **validated_data
            )
        
        return cart_item

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'item_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

# Order Serializers
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'store', 'store_name', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'product_name', 'store_name', 'subtotal']

class OrderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'total_amount', 'created_at']
        read_only_fields = ['id', 'order_number', 'total_amount', 'created_at']

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shipping_address = AddressSerializer(read_only=True)
    customer = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'status', 
            'shipping_address', 'total_amount', 'shipping_cost',
            'notes', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'customer', 'total_amount', 
            'items', 'created_at', 'updated_at'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    shipping_address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(),
        source='shipping_address'
    )
    
    class Meta:
        model = Order
        fields = ['shipping_address_id', 'notes']
    
    def validate_shipping_address_id(self, value):
        # Vérifier que l'adresse appartient à l'utilisateur
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Cette adresse ne vous appartient pas.")
        return value
    
    def create(self, validated_data):
        user = self.context['request'].user
        
        # Récupérer le panier de l'utilisateur
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            raise serializers.ValidationError("Votre panier est vide.")
        
        # Vérifier que le panier n'est pas vide
        if cart.items.count() == 0:
            raise serializers.ValidationError("Votre panier est vide.")
        
        # Calculer le montant total
        total_amount = cart.total
        shipping_cost = 0  # À calculer en fonction de règles de livraison
        
        # Créer la commande
        order = Order.objects.create(
            customer=user,
            shipping_address=validated_data.get('shipping_address'),
            total_amount=total_amount,
            shipping_cost=shipping_cost,
            notes=validated_data.get('notes', '')
        )
        
        # Créer les éléments de commande à partir du panier
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                store=item.product.store,
                quantity=item.quantity,
                price=item.product.price
            )
        
        # Vider le panier
        cart.items.all().delete()
        
        return order

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
    
    def validate_status(self, value):
        # Vérifier que le statut est valide pour la transition
        current_status = self.instance.status
        valid_transitions = {
            'pending': ['paid', 'cancelled'],
            'paid': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'cancelled'],
            'delivered': [],  # Statut final
            'cancelled': []   # Statut final
        }
        
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Transition de statut invalide: de '{current_status}' à '{value}'."
            )
        
        return value