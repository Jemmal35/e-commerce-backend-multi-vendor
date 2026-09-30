import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        VENDOR = 'vendor', 'Vendor'
        ADMIN = 'admin', 'Admin'
        
    id = models.UUIDField(primary_key= True, default= uuid.uuid4, editable= False)
    email = models.EmailField(unique= True)
    role = models.CharField(max_length=20, choices=Role, default=Role.CUSTOMER)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return f"{self.email}- {self.role}"
    

class UserProfile(models.Model):
    id = models.UUIDField(primary_key= True, default= uuid.uuid4, editable= False)
    user = models.OneToOneField(User, on_delete= models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null= True, blank= True)
    bio = models.TextField(blank= True, default= '')
    phone_number = models.CharField(max_length=20, blank= True, default='')
    address = models.CharField(max_length=255, blank= True, default='')
    city = models.CharField(max_length=255, blank= True, default='')
    country = models.CharField(max_length= 100, blank= True, default='')
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now= True)
    
    def __str__(self):
        return f"Profile of {self.user.email}"