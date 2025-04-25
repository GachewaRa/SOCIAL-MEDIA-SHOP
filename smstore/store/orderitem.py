from django.db import models
from .product import Product
from .order import Order



class OrderItem(models.Model):
    """Model representing an item within an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    
    # Original price at time of order
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Final price (may differ from original if renegotiated)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in Order {self.order.order_code}"
    
    def save(self, *args, **kwargs):
        # If final price not set, use original price
        if self.final_price is None:
            self.final_price = self.price
        super().save(*args, **kwargs)
    
    @property
    def subtotal(self):
        """Calculate original subtotal"""
        return self.price * self.quantity
        
    @property
    def final_subtotal(self):
        """Calculate final subtotal"""
        return self.final_price * self.quantity
