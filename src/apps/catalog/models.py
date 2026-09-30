import uuid

from django.db import models
from django.conf import settings
from django.utils.text import slugify

from apps.vendors.models import Vendor


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    parent = models.ForeignKey(
            "self", on_delete=models.CASCADE, null=True, blank=True, related_name="subcategories"
        )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        full_path = [self.name]
        parent = self.parent
        while parent is not None:
            full_path.append(parent.name)
            parent = parent.parent  
        return " -> ".join(full_path[::-1])
    

class ProductStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"
    OUT_OF_STOCK = "out_of_stock", "Out of Stock"
    

class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True, blank = True)
    stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.DRAFT,
    )
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    review_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.vendor.name})"
    
    
class ProductImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="product_images/")
    is_primary = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        return f"Image for {self.product.name}"
    

class ProductVariant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=100, unique=True, blank= True)
    attribute = models.JSONField(blank=True, null=True)  # e.g., {"size": "M", "color": "Red"}
    price_delta = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price difference from the base product price. Can be positive or negative.")
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    class Meta:
        ordering = ["sku"]

    def __str__(self):
        return f" ({self.product.name}) - {self.sku}"
    
class BulkUploadStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    
    
class BulkUploadJob(models.Model):
    id = models.UUIDField(primary_key= True, default= uuid.uuid4, editable= False)
    vendor = models.ForeignKey(Vendor, on_delete= models.CASCADE, related_name= 'bulk_uploads') 
    file = models.FileField(upload_to= 'bulk_uploads/sources/')
    error_report = models.FileField(upload_to= 'bulk_uploads/reports/', blank= True, null= True)
    status = models.CharField(max_length= 20, choices= BulkUploadStatus.choices, default= BulkUploadStatus.PENDING)
    total_rows = models.IntegerField(default= 0)
    processed_rows = models.IntegerField(default= 0)
    success_count = models.IntegerField(default= 0)
    error_count = models.IntegerField(default= 0)
    
    created_at = models.DateField(auto_now_add= True)
    updated_at = models.DateField(auto_now= True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Job {self.id} ({self.status})"