from django.db import models
from .product import Product
from store.order import Order
from .orderitem import OrderItem
from .storemodel import Store
from django.db.models.signals import post_save
from django.dispatch import receiver




class ShoppingCart(models.Model):
    """Model representing a temporary shopping cart"""
    session_key = models.CharField(max_length=40)
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Cart for session {self.session_key} at {self.store.name}"
    
    def add_item(self, product, quantity=1):
        """Add item to cart"""
        # Check if product already in cart
        try:
            cart_item = self.cartitem_set.get(product=product)
            cart_item.quantity += quantity
            cart_item.save()
        except CartItem.DoesNotExist:
            CartItem.objects.create(
                cart=self,
                product=product,
                quantity=quantity,
                price=product.price
            )
    
    def remove_item(self, product):
        """Remove item from cart"""
        try:
            cart_item = self.cartitem_set.get(product=product)
            cart_item.delete()
        except CartItem.DoesNotExist:
            pass
    
    def update_quantity(self, product, quantity):
        """Update quantity of item in cart"""
        try:
            cart_item = self.cartitem_set.get(product=product)
            if quantity <= 0:
                cart_item.delete()
            else:
                cart_item.quantity = quantity
                cart_item.save()
        except CartItem.DoesNotExist:
            if quantity > 0:
                CartItem.objects.create(
                    cart=self,
                    product=product,
                    quantity=quantity,
                    price=product.price
                )
    
    def clear(self):
        """Clear all items from cart"""
        self.cartitem_set.all().delete()
    
    def total(self):
        """Calculate total price of cart"""
        return sum(item.subtotal for item in self.cartitem_set.all())
    
    def convert_to_order(self, customer_name, customer_phone, delivery_location):
        """Convert cart to an order"""
        # Create order
        order = Order.objects.create(
            store=self.store,
            customer_name=customer_name,
            customer_phone=customer_phone,
            delivery_location=delivery_location,
            total_amount=self.total()
        )
        
        # Create order items
        for cart_item in self.cartitem_set.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.price
            )
        
        # Clear cart
        self.clear()
        
        # Send notification
        order.send_notification_email()
        
        return order


class CartItem(models.Model):
    """Model representing an item in a shopping cart"""
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at time of adding to cart
    added_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in cart {self.cart.id}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this cart item"""
        return self.price * self.quantity


@receiver(post_save, sender=Order)
def order_created_notification(sender, instance, created, **kwargs):
    """Send notification when a new order is created"""
    if created:
        instance.send_notification_email()