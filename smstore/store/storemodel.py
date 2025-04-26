from django.db import models
from django.contrib.auth.models import User


class Store(models.Model):
    """Model representing a store in the multi-tenant system"""
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='store_logos/', blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def total_revenue(self):
        """Calculate total revenue from all fulfilled orders"""
        return sum(order.final_total_amount for order in self.order_set.filter(status='fulfilled'))
    
    def total_orders(self):
        """Count total orders"""
        return self.order_set.count()
    
    def pending_orders(self):
        """Count pending orders"""
        return self.order_set.exclude(status='fulfilled').count()












