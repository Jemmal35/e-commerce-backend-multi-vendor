import uuid
from apps.vendors.models import Vendor
from django.db import models
from django.conf import settings


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    PROCESSING = "processing", "Processing"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"
    REFUNDED = "refunded", "Refunded"
    
class PaymentStatus(models.TextChoices):
    REQUIRES_ACTION = "requires_action", "Requires Action"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    REFUNDED = "refunded", "Refunded"
    
class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="orders")
    coupon = models.ForeignKey('cart.Coupon', on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PROCESSING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.JSONField(default=dict, help_text="Snapshot of the shipping address at checkout time")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"Order {self.id} for {self.user.username}"
    
    
class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name="order_items")
    variant = models.ForeignKey('catalog.ProductVariant', on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        
    def __str__(self):
        variant_name = f" ({self.variant.name})" if self.variant else ""
        return f"{self.quantity} x {self.product.name}{variant_name} for Order {self.order.id}"
    


class DisputeStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under Review"
    RESOLVED = "resolved", "Resolved"
    CLOSED_CUSTOMER_WON = "closed_customer", "Closed - Customer Won"
    CLOSED_VENDOR_WON = "closed_vendor", "Closed - Vendor Won"
    

class Dispute(models.Model):
    id = models.UUIDField(primary_key= True, editable= False, default= uuid.uuid4)
    order = models.OneToOneField(Order, on_delete= models.CASCADE, related_name= "dispute")
    reason = models.CharField(max_length= 255)
    description = models.TextField()
    status = models.CharField(max_length= 50, choices= DisputeStatus.choices, default= DisputeStatus.OPEN, db_index= True)
    resolution_notes = models.TextField(blank= True, null= True)
    created_at = models.DateTimeField(auto_now_add= True)
    updated_at = models.DateTimeField(auto_now= True)
    

    class Meta:
        ordering = ["-created_at"]
        
    def __str__(self):
        return f"Dipute for Order {self.order.id} - {self.status}"