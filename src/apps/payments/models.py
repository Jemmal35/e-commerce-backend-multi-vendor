import uuid 
from django.db import models

from apps.orders.models import Order

class PaymentStatus(models.TextChoices):
    REQUIRES_ACTION = "requires_action", "Requires Action"
    PROCESSING = "processing", "Processing"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
    REFUNDED = "refunded", "Refunded"

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="payments", db_index=True)
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    payment_method = models.CharField(max_length=50, default="card")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.REQUIRES_ACTION,
        db_index=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Stores raw gateway metadata, failure reasons, or refund details.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["order", "status"]),
        ]
        
    def __str__(self):
        return f"Payment {self.id} [Status: {self.status}] for Order {self.order.id}"