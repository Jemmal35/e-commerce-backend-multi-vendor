import uuid
from django.db import models
from django.utils import timezone

from apps.catalog.models import Product, ProductVariant
from  django.conf import settings

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carts")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart {self.id} for {self.user.username}"
    
class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensures a user can't have duplicate rows of the exact same product+variant combination
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product', 'variant'], 
                name='unique_cart_product_variant'
            )
        ]

    def __str__(self):
        variant_name = f" ({self.variant.name})" if self.variant else ""
        return f"{self.quantity} x {self.product.name}{variant_name}"


class DiscountType(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage'
    FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'

class Coupon(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Optional limit on how many times the coupon can be used")  # Optional limit on how many times the coupon can be used    
    per_user_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Optional limit on how many times a single user can use the coupon")  # Optional limit on how many times a single user can use the coupon
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Optional minimum order value to apply the coupon")  # Optional minimum order value to apply the coupon
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Coupon {self.code} - {self.discount_type} - {self.discount_value}"
    
    @property
    def is_valid(self):
        now = timezone.now()
        return self.is_active and self.valid_from <= now <= self.valid_to
    

class CouponUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="usages")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coupon_usages")
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents redundant tracking records if handled per order, but 
        # allows multiple records if per_user_limit > 1.
        indexes = [
            models.Index(fields=['coupon', 'user']),
        ]
        

    def __str__(self):
        return f"Coupon {self.coupon.code} used by {self.user.username} at {self.used_at}"