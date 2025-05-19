from django.db import models
from .storemodel import Store
from cloudinary.models import CloudinaryField

class Product(models.Model):
    """Model representing a product in the store"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)
    inventory = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.store.name}"
    
    def update_stats(self, quantity_sold, revenue_made):
        """Update sales statistics for this product"""
        self.units_sold += quantity_sold
        self.total_revenue += revenue_made
        self.save()