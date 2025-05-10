from rest_framework import viewsets, generics, status, permissions
from rest_framework.decorators import action 
from rest_framework.response import Response 
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

# from rest_framework.authentication import SessionAuthentication

# class CsrfExemptSessionAuthentication(SessionAuthentication):
#     def enforce_csrf(self, request):
#         return

# In your views.py
from django.http import HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token

from django.http import JsonResponse

# @ensure_csrf_cookie
# def get_csrf_token(request):
#     response = HttpResponse()
#     response["X-CSRF-Set"] = "Attempted"  # Debug header
#     return response

@ensure_csrf_cookie
def get_csrf_token(request):
    """
    Returns the CSRF token both as a cookie and in the response body.
    This helps with cross-origin scenarios where cookies might be blocked.
    """
    token = get_token(request)
    return JsonResponse({
        'csrf_token': token,
        'status': 'success'
    })

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

class IsAuthenticatedForWriteOrReadOnly(permissions.BasePermission):
    """
    Allow read access to anyone, but require authentication for write operations.
    """
    def has_permission(self, request, view):
        # Read permissions are allowed to anyone
        if request.method in permissions.SAFE_METHODS:
            return True
        # Write permissions require authentication
        return bool(request.user and request.user.is_authenticated)
    


class StoreViewSet(viewsets.ModelViewSet):
    serializer_class = StoreSerializer
    permission_classes = [IsAuthenticatedForWriteOrReadOnly, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        # For list view and anonymous users, return all stores
        if not self.request.user.is_authenticated:
            return Store.objects.all()
        
        # For authenticated users
        if self.request.user.is_superuser:
            return Store.objects.all()
        return Store.objects.filter(owner=self.request.user)
    
    def get_object(self):
        # For detail views, use the standard method which will apply object-level permissions
        # after retrieving the object
        if self.action in ['retrieve', 'products', 'orders']:
            # For retrieve actions, get from the entire queryset
            queryset = Store.objects.all()
            # Look up by primary key provided in URL
            obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
            # Check object-level permissions
            self.check_object_permissions(self.request, obj)
            return obj
        return super().get_object()
    
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
    permission_classes = [IsAuthenticatedForWriteOrReadOnly, IsOwnerOrReadOnly]
    
    def get_queryset(self):

        if not self.request.user.is_authenticated:
            return Product.objects.all()
         
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
    # authentication_classes = (CsrfExemptSessionAuthentication,)
    
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
        # Debug info
        session_key = request.session.session_key
        store_id = kwargs.get('store_id')
        
        if not session_key:
            request.session.create()  # Force session creation if missing
            session_key = request.session.session_key
            return Response(
                {"error": "No session found - new session created, please try again"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        store = get_object_or_404(Store, pk=store_id)
        
        # More detailed error for troubleshooting
        try:
            cart = ShoppingCart.objects.get(session_key=session_key, store=store)
        except ShoppingCart.DoesNotExist:
            # Check if any cart exists for this session
            any_cart = ShoppingCart.objects.filter(session_key=session_key).first()
            
            # Debug response with more info
            debug_info = {
                "error": "No active shopping cart found",
                "debug": {
                    "session_key": session_key,
                    "session_exists": session_key is not None,
                    "store_id": store_id,
                    "has_other_cart": any_cart is not None,
                    "other_cart_store": any_cart.store.id if any_cart else None
                }
            }
            return Response(debug_info, status=status.HTTP_400_BAD_REQUEST)
            
        if not cart.cartitem_set.exists():
            return Response(
                {"error": "Your cart is empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate request data
        serializer = self.get_serializer(data=request.data, context={'cart': cart})
        
        if not serializer.is_valid():
            # Return detailed validation errors
            return Response(
                {
                    "error": "Invalid order data",
                    "details": serializer.errors,
                    "received_data": request.data
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        order = serializer.save()
        
        # Return the created order
        order_serializer = OrderSerializer(order)
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)


class TrackOrderView(generics.GenericAPIView):
    """Track an order using its unique code"""
    serializer_class = OrderTrackingSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # print("Request Data:", request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order = serializer.validated_data['order_code']
        order_serializer = OrderSerializer(order)
        # print("SERIALIZED Data:", order_serializer.data)
        return Response(order_serializer.data)

