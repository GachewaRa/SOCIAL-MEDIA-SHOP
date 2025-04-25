from django.db import models
from .storemodel import Store
# from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
import random
import string
from datetime import datetime

class OrderManager(models.Manager):
    """Manager for Order model with additional functionality"""
    
    def generate_order_code(self, store):
        """Generate a unique, user-friendly order code"""
        # Get current day of year (1-366)
        day_of_year = datetime.now().timetuple().tm_yday
        day_str = f"{day_of_year:02d}"
        
        # Get store prefix (first two letters of store name)
        store_prefix = store.name[:2].upper()
        
        # Generate random characters
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=2))
        
        # Create base code
        base_code = f"{store_prefix}{day_str}{random_part}"
        
        # Add a simple checksum (sum of ASCII values mod 36, represented as alphanumeric)
        checksum_value = sum(ord(c) for c in base_code) % 36
        checksum = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'[checksum_value]
        
        full_code = f"{base_code}{checksum}"
        
        # Check if code already exists and regenerate if needed
        if Order.objects.filter(order_code=full_code).exists():
            return self.generate_order_code(store)  # Recursive call for new code
            
        return full_code


class Order(models.Model):
    """Model representing a customer order"""
    STATUS_CHOICES = [
        ('placed', 'Order Placed'),
        ('confirmed', 'Order Confirmed'),
        ('in_delivery', 'In Delivery'),
        ('fulfilled', 'Fulfilled'),
        ('cancelled', 'Cancelled'),
    ]
    
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    delivery_location = models.TextField()
    
    # Original order details
    order_code = models.CharField(max_length=10, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Final details (after fulfillment, may differ from original)
    final_total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='placed')
    notes = models.TextField(blank=True)
    
    placed_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = OrderManager()
    
    def __str__(self):
        return f"Order {self.order_code} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        # Generate order code if this is a new order
        if not self.order_code and not self.id:
            self.order_code = Order.objects.generate_order_code(self.store)
            
        # If being marked as fulfilled
        if self.status == 'fulfilled' and not self.fulfilled_at:
            self.fulfilled_at = timezone.now()
            
            # If final amount not set, use the original
            if self.final_total_amount is None:
                self.final_total_amount = self.total_amount
                
        super().save(*args, **kwargs)
    
    def mark_fulfilled(self, final_amount=None):
        """Mark order as fulfilled and update product inventory"""
        self.status = 'fulfilled'
        if final_amount is not None:
            self.final_total_amount = final_amount
        else:
            self.final_total_amount = self.total_amount
            
        self.fulfilled_at = timezone.now()
        self.save()
        
        # Update product stats and inventory
        for item in self.orderitem_set.all():
            product = item.product
            product.inventory -= item.quantity
            product.update_stats(item.quantity, item.final_price * item.quantity)
            product.save()
    
    def send_notification_email(self):
        """Send notification email to store owner"""
        subject = f"New Order: {self.order_code}"
        message = f"""
        New order received!
        
        Order Code: {self.order_code}
        Customer: {self.customer_name}
        Phone: {self.customer_phone}
        Delivery Location: {self.delivery_location}
        Total Amount: {self.total_amount}
        
        Order Items:
        {', '.join([f"{item.quantity}x {item.product.name}" for item in self.orderitem_set.all()])}
        
        Please confirm this order in your admin dashboard.
        """
        
        send_mail(
            subject,
            message,
            'noreply@yourshop.com',  # From email
            [self.store.email],  # To email
            fail_silently=False,
        )