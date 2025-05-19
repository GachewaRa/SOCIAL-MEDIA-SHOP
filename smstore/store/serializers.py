from rest_framework import serializers
from django.db import transaction
from django.contrib.auth.models import User

from .order import Order
from .orderitem import OrderItem
from .product import Product
from .shoppingcart import CartItem, ShoppingCart
from .storemodel import Store



class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


# class StoreSerializer(serializers.ModelSerializer):
#     owner = UserSerializer(read_only=True)
#     total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
#     total_orders = serializers.IntegerField(read_only=True)
#     pending_orders = serializers.IntegerField(read_only=True)
    
#     class Meta:
#         model = Store
#         fields = ['id', 'name', 'owner', 'description', 'logo', 'email', 'phone', 
#                   'created_at', 'updated_at', 'total_revenue', 'total_orders', 'pending_orders']
#         read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['total_revenue'] = instance.total_revenue()
#         representation['total_orders'] = instance.total_orders()
#         representation['pending_orders'] = instance.pending_orders()
#         return representation

class StoreSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_orders = serializers.IntegerField(read_only=True)
    pending_orders = serializers.IntegerField(read_only=True)
    logo = serializers.SerializerMethodField()  # Add this line

    class Meta:
        model = Store
        fields = ['id', 'name', 'owner', 'description', 'logo', 'email', 'phone', 
                 'created_at', 'updated_at', 'total_revenue', 'total_orders', 'pending_orders']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def get_logo(self, obj):
        """Returns the full Cloudinary URL for the logo."""
        if obj.logo:
            return f"https://res.cloudinary.com/dyr0ityfq/{obj.logo}"
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['total_revenue'] = instance.total_revenue()
        representation['total_orders'] = instance.total_orders()
        representation['pending_orders'] = instance.pending_orders()
        return representation


# class ProductSerializer(serializers.ModelSerializer):
#     store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    
#     class Meta:
#         model = Product
#         fields = ['id', 'store', 'name', 'description', 'price', 'image', 
#                   'inventory', 'units_sold', 'total_revenue', 'created_at', 'updated_at']
#         read_only_fields = ['id', 'units_sold', 'total_revenue', 'created_at', 'updated_at']
    
#     def validate_store(self, value):
#         # Ensure users can only create products for their own stores
#         request = self.context.get('request')
#         if request and request.user.is_authenticated:
#             if not request.user.is_superuser and value.owner != request.user:
#                 raise serializers.ValidationError("You can only create products for your own stores.")
#         return value

class ProductSerializer(serializers.ModelSerializer):
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    image = serializers.SerializerMethodField()  # Add this line

    class Meta:
        model = Product
        fields = ['id', 'store', 'name', 'description', 'price', 'image', 
                 'inventory', 'units_sold', 'total_revenue', 'created_at', 'updated_at']
        read_only_fields = ['id', 'units_sold', 'total_revenue', 'created_at', 'updated_at']

    def get_image(self, obj):
        """Returns the full Cloudinary URL for the product image."""
        if obj.image:
            return f"https://res.cloudinary.com/dyr0ityfq/{obj.image}"
        return None

    def validate_store(self, value):
        # Ensure users can only create products for their own stores
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if not request.user.is_superuser and value.owner != request.user:
                raise serializers.ValidationError("You can only create products for your own stores.")
        return value

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    final_subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'final_price', 
                  'subtotal', 'final_subtotal']
        read_only_fields = ['id', 'price', 'subtotal', 'final_subtotal']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['subtotal'] = instance.subtotal
        representation['final_subtotal'] = instance.final_subtotal
        return representation


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    
    class Meta:
        model = Order
        fields = ['id', 'store', 'order_code', 'customer_name', 'customer_phone', 
                  'delivery_location', 'status', 'total_amount', 'final_total_amount', 
                  'notes', 'placed_at', 'fulfilled_at', 'updated_at', 'items']
        read_only_fields = ['id', 'order_code', 'placed_at', 'fulfilled_at', 'updated_at']
    
    def validate_store(self, value):
        # Ensure users can only access their own stores
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if not request.user.is_superuser and value.owner != request.user:
                raise serializers.ValidationError("You can only create orders for your own stores.")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True)
    
    class Meta:
        model = Order
        fields = ['status', 'final_total_amount', 'notes', 'items']
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('orderitem_set', None)
        
        # Update order fields
        instance.status = validated_data.get('status', instance.status)
        instance.notes = validated_data.get('notes', instance.notes)
        
        # Handle fulfillment logic
        if instance.status == 'fulfilled' and not instance.fulfilled_at:
            instance.final_total_amount = validated_data.get('final_total_amount', instance.total_amount)
            instance.mark_fulfilled(instance.final_total_amount)
        else:
            instance.final_total_amount = validated_data.get('final_total_amount', instance.final_total_amount)
            instance.save()
        
        # Update order items if provided
        if items_data:
            for item_data in items_data:
                order_item = OrderItem.objects.get(id=item_data.get('id'))
                order_item.final_price = item_data.get('final_price', order_item.price)
                order_item.quantity = item_data.get('quantity', order_item.quantity)
                order_item.save()
        
        return instance


# class CartItemSerializer(serializers.ModelSerializer):
#     product_name = serializers.ReadOnlyField(source='product.name')
#     product_price = serializers.ReadOnlyField(source='product.price')
#     product_image = serializers.SerializerMethodField() 
#     subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
#     class Meta:
#         model = CartItem
#         fields = ['id', 'product', 'product_name', 'product_price', 'product_image', 'quantity', 'price', 'subtotal']
#         read_only_fields = ['id', 'price', 'subtotal']
    
#     def get_product_image(self, obj):
#         """Method to get the product image URL"""
#         if obj.product.image:
#             return self.context['request'].build_absolute_uri(obj.product.image.url)
#         return None
    
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['subtotal'] = instance.subtotal
#         return representation

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    product_price = serializers.ReadOnlyField(source='product.price')
    product_image = serializers.SerializerMethodField() 
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'product_price', 'product_image', 'quantity', 'price', 'subtotal']
        read_only_fields = ['id', 'price', 'subtotal']
    
    def get_product_image(self, obj):
        """Returns the full Cloudinary URL for the product image."""
        if obj.product.image:
            return f"https://res.cloudinary.com/dyr0ityfq/{obj.product.image}"
        return None
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['subtotal'] = instance.subtotal
        return representation


class ShoppingCartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source='cartitem_set', many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = ShoppingCart
        fields = ['id', 'session_key', 'store', 'created_at', 'updated_at', 'items', 'total']
        read_only_fields = ['id', 'session_key', 'created_at', 'updated_at', 'total']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['total'] = instance.total()
        return representation


class CartItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    
    def validate_product_id(self, value):
        try:
            product = Product.objects.get(pk=value)
            if product.inventory < self.initial_data.get('quantity', 1):
                raise serializers.ValidationError("Not enough items in inventory.")
            return value
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product does not exist.")


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)
    
    def validate_quantity(self, value):
        if value == 0:
            return value  # Handle removal in the view
        
        cart_item = self.instance
        if cart_item.product.inventory < value:
            raise serializers.ValidationError("Not enough items in inventory.")
        
        return value


class CheckoutSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=100)
    customer_phone = serializers.CharField(max_length=20)
    delivery_location = serializers.CharField()
    
    @transaction.atomic
    def create(self, validated_data):
        cart = self.context.get('cart')
        if not cart or not cart.cartitem_set.exists():
            raise serializers.ValidationError("Cart is empty.")
        
        # Create order from cart
        order = cart.convert_to_order(
            customer_name=validated_data.get('customer_name'),
            customer_phone=validated_data.get('customer_phone'),
            delivery_location=validated_data.get('delivery_location')
        )
        
        return order


class OrderTrackingSerializer(serializers.Serializer):
    order_code = serializers.CharField(max_length=10)
    
    def validate_order_code(self, value):
        try:
            return Order.objects.get(order_code=value)
        except Order.DoesNotExist:
            raise serializers.ValidationError("Order not found.")