from django.contrib import admin
from .order import Order
from .orderitem import OrderItem
from .shoppingcart import CartItem, ShoppingCart
from .storemodel import Store

from .product import Product


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ('name', 'price', 'inventory', 'units_sold')
    show_change_link = True


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'final_price', 'subtotal', 'final_subtotal')
    readonly_fields = ('subtotal', 'final_subtotal')

    def subtotal(self, obj):
        return obj.subtotal
    
    def final_subtotal(self, obj):
        return obj.final_subtotal


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ('product', 'quantity', 'price', 'subtotal')
    readonly_fields = ('subtotal',)

    def subtotal(self, obj):
        return obj.subtotal


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'email', 'phone', 'total_orders', 'pending_orders', 'total_revenue')
    search_fields = ('name', 'owner__username', 'email')
    list_filter = ('created_at',)
    inlines = [ProductInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(owner=request.user)
        return qs


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'store', 'price', 'inventory', 'units_sold', 'total_revenue')
    list_filter = ('store', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('units_sold', 'total_revenue')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show products from stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(store__owner=request.user)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit store choices to stores owned by the current user
        if db_field.name == "store" and not request.user.is_superuser:
            kwargs["queryset"] = Store.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'store', 'customer_name', 'status', 'total_amount', 
                    'final_total_amount', 'placed_at', 'fulfilled_at')
    list_filter = ('store', 'status', 'placed_at', 'fulfilled_at')
    search_fields = ('order_code', 'customer_name', 'customer_phone')
    readonly_fields = ('order_code', 'placed_at', 'fulfilled_at')
    inlines = [OrderItemInline]
    fieldsets = (
        ('Order Information', {
            'fields': ('store', 'order_code', 'status', 'notes')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_phone', 'delivery_location')
        }),
        ('Financial Details', {
            'fields': ('total_amount', 'final_total_amount')
        }),
        ('Timestamps', {
            'fields': ('placed_at', 'fulfilled_at')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show orders from stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(store__owner=request.user)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit store choices to stores owned by the current user
        if db_field.name == "store" and not request.user.is_superuser:
            kwargs["queryset"] = Store.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def save_model(self, request, obj, form, change):
        # Handle fulfillment logic when status changes to 'fulfilled'
        if 'status' in form.changed_data and obj.status == 'fulfilled':
            obj.mark_fulfilled(obj.final_total_amount)
        else:
            super().save_model(request, obj, form, change)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'order', 'quantity', 'price', 'final_price', 'subtotal', 'final_subtotal')
    list_filter = ('order__status', 'order__store')
    search_fields = ('order__order_code', 'product__name')
    readonly_fields = ('subtotal', 'final_subtotal')
    
    def subtotal(self, obj):
        return obj.subtotal
    subtotal.short_description = 'Original Subtotal'
    
    def final_subtotal(self, obj):
        return obj.final_subtotal
    final_subtotal.short_description = 'Final Subtotal'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show order items from stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(order__store__owner=request.user)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit choices based on user permissions
        if not request.user.is_superuser:
            if db_field.name == "order":
                kwargs["queryset"] = Order.objects.filter(store__owner=request.user)
            elif db_field.name == "product":
                kwargs["queryset"] = Product.objects.filter(store__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'store', 'session_key', 'total', 'created_at', 'updated_at')
    list_filter = ('store', 'created_at')
    search_fields = ('session_key',)
    inlines = [CartItemInline]
    
    def total(self, obj):
        return obj.total()
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show carts from stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(store__owner=request.user)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit store choices to stores owned by the current user
        if db_field.name == "store" and not request.user.is_superuser:
            kwargs["queryset"] = Store.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Optional: Register CartItem separately (might not be needed since it's available as inline)
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'quantity', 'price', 'subtotal', 'added_at')
    list_filter = ('cart__store', 'added_at')
    search_fields = ('product__name',)
    
    def subtotal(self, obj):
        return obj.subtotal
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show cart items from stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(cart__store__owner=request.user)
        return qs
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit choices based on user permissions
        if not request.user.is_superuser:
            if db_field.name == "cart":
                kwargs["queryset"] = ShoppingCart.objects.filter(store__owner=request.user)
            elif db_field.name == "product":
                kwargs["queryset"] = Product.objects.filter(store__owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
