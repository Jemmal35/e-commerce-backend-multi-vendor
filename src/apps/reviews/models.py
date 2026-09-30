import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.catalog.models import Product

class Review(models.Model):
    id = models.UUIDField(default= uuid.uuid4, primary_key= True, editable= False)
    product = models.ForeignKey(Product, on_delete= models.CASCADE, related_name= 'reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete= models.CASCADE)
    rating  = models.IntegerField(validators= [MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank= True)
    created_at = models.DateTimeField(auto_now_add= True)
    
    class Meta:
        unique_together = ('product', 'user') # One review per user per product