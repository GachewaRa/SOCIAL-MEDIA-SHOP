# api/views.py
from rest_framework import viewsets, generics, status, permissions # type: ignore
from rest_framework.decorators import action # type: ignore
from rest_framework.response import Response # type: ignore
from django.shortcuts import get_object_or_404
from .order import Order
from .product import Product
from .shoppingcart import CartItem, ShoppingCart
from .storemodel import Store
from .serializers import (
    StoreSerializer, ProductSerializer, OrderSerializer, OrderUpdateSerializer,
    ShoppingCartSerializer, CartItemSerializer, CartItemCreateSerializer,
    CartItemUpdateSerializer, CheckoutSerializer, OrderTrackingSerializer
)


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'store'):
            return obj.store.owner == request.user
        return False


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Store.objects.all()
        return Store.objects.filter(owner=user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        store = self.get_object()
        products = Product.objects.filter(store=store)
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def orders(self, request, pk=None):
        store = self.get_object()
        orders = Order.objects.filter(store=store)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Product.objects.all()
        return Product.objects.filter(store__owner=user)


class StoreProductsPublicView(generics.ListAPIView):
    """Public endpoint to view products for a specific store"""
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        store_id = self.kwargs.get('store_id')
        return Product.objects.filter(store_id=store_id)


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return OrderUpdateSerializer
        return OrderSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(store__owner=user)


class CartView(generics.RetrieveAPIView):
    """View for managing shopping cart"""
    serializer_class = ShoppingCartSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        session_key = self.request.session.session_key
        if not session_key:
            self.request.session.create()
            session_key = self.request.session.session_key
        
        store_id = self.kwargs.get('store_id')
        store = get_object_or_404(Store, pk=store_id)
        
        cart, created = ShoppingCart.objects.get_or_create(
            session_key=session_key,
            store=store
        )
        return cart


class AddToCartView(generics.CreateAPIView):
    """Add an item to the cart"""
    serializer_class = CartItemCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        store_id = kwargs.get('store_id')
        store = get_object_or_404(Store, pk=store_id)
        
        cart, created = ShoppingCart.objects.get_or_create(
            session_key=session_key,
            store=store
        )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']
        product = get_object_or_404(Product, pk=product_id, store=store)
        
        cart.add_item(product, quantity)
        
        # Return the updated cart
        cart_serializer = ShoppingCartSerializer(cart)
        return Response(cart_serializer.data, status=status.HTTP_201_CREATED)


class UpdateCartItemView(generics.UpdateAPIView):
    """Update quantity of an item in the cart"""
    serializer_class = CartItemUpdateSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        cart_item_id = self.kwargs.get('item_id')
        session_key = self.request.session.session_key
        return get_object_or_404(CartItem, pk=cart_item_id, cart__session_key=session_key)
    
    def update(self, request, *args, **kwargs):
        cart_item = self.get_object()
        serializer = self.get_serializer(cart_item, data=request.data)
        serializer.is_valid(raise_exception=True)
        
        quantity = serializer.validated_data['quantity']
        
        if quantity == 0:
            cart_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        cart_item.quantity = quantity
        cart_item.save()
        
        # Return the updated cart
        cart_serializer = ShoppingCartSerializer(cart_item.cart)
        return Response(cart_serializer.data)


class RemoveFromCartView(generics.DestroyAPIView):
    """Remove an item from the cart"""
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        cart_item_id = self.kwargs.get('item_id')
        session_key = self.request.session.session_key
        return get_object_or_404(CartItem, pk=cart_item_id, cart__session_key=session_key)
    
    def destroy(self, request, *args, **kwargs):
        cart_item = self.get_object()
        cart = cart_item.cart
        cart_item.delete()
        
        # Return the updated cart
        cart_serializer = ShoppingCartSerializer(cart)
        return Response(cart_serializer.data)


class CheckoutView(generics.CreateAPIView):
    """Convert cart to an order"""
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        session_key = request.session.session_key
        if not session_key:
            return Response(
                {"error": "No active shopping cart found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        store_id = kwargs.get('store_id')
        store = get_object_or_404(Store, pk=store_id)
        
        try:
            cart = ShoppingCart.objects.get(session_key=session_key, store=store)
        except ShoppingCart.DoesNotExist:
            return Response(
                {"error": "No active shopping cart found"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not cart.cartitem_set.exists():
            return Response(
                {"error": "Your cart is empty"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data, context={'cart': cart})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Return the created order
        order_serializer = OrderSerializer(order)
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)


class TrackOrderView(generics.GenericAPIView):
    """Track an order using its unique code"""
    serializer_class = OrderTrackingSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = serializer.validated_data['order_code']
        order_serializer = OrderSerializer(order)
        
        return Response(order_serializer.data)

