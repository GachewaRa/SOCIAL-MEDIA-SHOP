from datetime import timezone
from django.contrib import admin
from .order import Order
from .orderitem import OrderItem
from .shoppingcart import CartItem, ShoppingCart
from .storemodel import Store
from .product import Product
from django import forms


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


class StoreAdminForm(forms.ModelForm):
    total_orders_count = forms.IntegerField(disabled=True, required=False, 
                                           label="Total Orders")
    pending_orders_count = forms.IntegerField(disabled=True, required=False,
                                             label="Pending Orders")
    total_revenue_amount = forms.DecimalField(disabled=True, required=False,
                                             label="Total Revenue")
    
    class Meta:
        model = Store
        fields = '__all__'  # Include all fields from the model
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the calculated fields if we have an instance
        if self.instance and self.instance.pk:
            self.initial['total_orders_count'] = self.instance.total_orders()
            self.initial['pending_orders_count'] = self.instance.pending_orders()
            self.initial['total_revenue_amount'] = self.instance.total_revenue()


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    form = StoreAdminForm
    list_display = ('name', 'owner', 'email', 'phone', 'display_total_orders', 'display_pending_orders', 'display_total_revenue')
    search_fields = ('name', 'owner__username', 'email')
    list_filter = ('created_at',)
    inlines = [ProductInline]
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If not superuser, only show stores owned by the current user
        if not request.user.is_superuser:
            qs = qs.filter(owner=request.user)
        return qs
    
    def display_total_orders(self, obj):
        return obj.total_orders()
    display_total_orders.short_description = 'Total Orders'
    
    def display_pending_orders(self, obj):
        return obj.pending_orders()
    display_pending_orders.short_description = 'Pending Orders'
    
    def display_total_revenue(self, obj):
        return obj.total_revenue()
    display_total_revenue.short_description = 'Total Revenue'


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


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     list_display = ('order_code', 'store', 'customer_name', 'status', 'total_amount', 
#                     'final_total_amount', 'placed_at', 'fulfilled_at')
#     list_filter = ('store', 'status', 'placed_at', 'fulfilled_at')
#     search_fields = ('order_code', 'customer_name', 'customer_phone')
#     readonly_fields = ('order_code', 'placed_at', 'fulfilled_at')
#     inlines = [OrderItemInline]
#     fieldsets = (
#         ('Order Information', {
#             'fields': ('store', 'order_code', 'status', 'notes')
#         }),
#         ('Customer Information', {
#             'fields': ('customer_name', 'customer_phone', 'delivery_location')
#         }),
#         ('Financial Details', {
#             'fields': ('total_amount', 'final_total_amount')
#         }),
#         ('Timestamps', {
#             'fields': ('placed_at', 'fulfilled_at')
#         }),
#     )
    
#     def get_readonly_fields(self, request, obj=None):
#         # For new orders, only make certain fields readonly
#         if obj is None:  # This is a new order being created
#             return ('order_code', 'placed_at', 'fulfilled_at')
#         # For existing orders, make more fields readonly
#         return ('order_code', 'placed_at', 'fulfilled_at')
    
#     def save_model(self, request, obj, form, change):
#         # If this is a new order (not a change to existing)
#         if not change:
#             # Let the save method generate the order code
#             super().save_model(request, obj, form, change)
#         else:
#             # If status is changing to fulfilled
#             if 'status' in form.changed_data and obj.status == 'fulfilled':
#                 obj.mark_fulfilled(obj.final_total_amount)
#             else:
#                 super().save_model(request, obj, form, change)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_code', 'store', 'customer_name', 'status', 'total_amount', 
                   'final_total_amount', 'placed_at', 'fulfilled_at')
    list_filter = ('store', 'status', 'placed_at', 'fulfilled_at')
    search_fields = ('order_code', 'customer_name', 'customer_phone')
    readonly_fields = ('order_code', 'placed_at', 'fulfilled_at', 'total_amount')  # Added total_amount as readonly
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
            'fields': ('placed_at', 'fulfilled_at'),
            'classes': ('collapse',)  # Optional: makes this section collapsible
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Dynamic readonly fields"""
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # Existing order
            return readonly_fields + ('store', 'customer_name', 'customer_phone', 'delivery_location')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        """Simplified save logic"""
        try:
            if change and 'status' in form.changed_data and obj.status == 'fulfilled':
                if hasattr(obj, 'mark_fulfilled'):
                    obj.mark_fulfilled(obj.final_total_amount)
                else:
                    obj.fulfilled_at = timezone.now()
            super().save_model(request, obj, form, change)
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Error saving order: {str(e)}")
            raise


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
