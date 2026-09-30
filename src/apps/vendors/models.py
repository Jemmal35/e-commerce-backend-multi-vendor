from django.db import models
import uuid
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.text import slugify

User = get_user_model()

class VENDOR_STATUS(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'   
    REJECTED = 'rejected', 'Rejected'
    SUSPENDED = 'suspended', 'Suspended'
    
class Vendor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    store_name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='vendors/logos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=VENDOR_STATUS.choices, default=VENDOR_STATUS.PENDING)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.store_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.slug or self._state.adding:
            base_slug = slugify(self.store_name)
            slug = base_slug
            self.slug = slug
        super().save(*args, **kwargs)
        
        

class VendorAnalyticsSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vendor = models.ForeignKey(
        Vendor, 
        on_delete=models.CASCADE, 
        related_name='analytics_snapshots'
    )
    date = models.DateField(db_index=True)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_orders = models.PositiveIntegerField(default=0)
    total_items_sold = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('vendor', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"Snapshot for {self.vendor.store_name} on {self.date}"