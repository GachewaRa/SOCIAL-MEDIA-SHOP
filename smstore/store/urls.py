# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    StoreViewSet, ProductViewSet, OrderViewSet, StoreProductsPublicView,
    CartView, AddToCartView, UpdateCartItemView, RemoveFromCartView,
    CheckoutView, TrackOrderView
)

router = DefaultRouter()
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    
    # Public endpoints
    path('public/stores/<int:store_id>/products/', StoreProductsPublicView.as_view(), name='public-store-products'),
    
    # Cart endpoints
    path('stores/<int:store_id>/cart/', CartView.as_view(), name='cart'),
    path('stores/<int:store_id>/cart/add/', AddToCartView.as_view(), name='add-to-cart'),
    path('cart/items/<int:item_id>/', UpdateCartItemView.as_view(), name='update-cart-item'),
    path('cart/items/<int:item_id>/remove/', RemoveFromCartView.as_view(), name='remove-from-cart'),
    
    # Checkout endpoint
    path('stores/<int:store_id>/checkout/', CheckoutView.as_view(), name='checkout'),
    
    # Order tracking
    path('track-order/', TrackOrderView.as_view(), name='track-order'),
]