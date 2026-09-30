from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.core.mail import send_mail
from django.conf import settings

from apps.catalog.models import Product, ProductVariant, ProductStatus
from .models import Order, OrderItem

@shared_task
def process_successful_payment_task(order_id):
    
    with transaction.atomic():
        try:
            order = Order.objects.select_related('user').get(id = order_id)
        except Order.DoesNotExist:
            return
        
        items = OrderItem.objects.filter(order = order).select_related('product','variant')
        
        for item in items:
            if item.variant:
                ProductVariant.objects.filter(id = item.variant_id).update(
                    stock = F("stock") - item.quantity
                )
            else:
                Product.objects.filter(id = item.product_id).update(
                    stock = F("stock") - item.quantity
                )
        
        send_mail(
            subject=f"Payment Confirmed - Order #{order.id}",
            message=f"Hello {order.user.username},\n\nYour payment of {order.total_amount} was successful. We are now processing your order.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=True,
        )
                
                
                
@shared_task
def process_failed_payment_task(order_id):
    
    try:
        order = Order.objects.select_related('user').get(id = order_id)
    except Order.DoesNotExist:
        return
    
    send_mail(
        subject=f"Payment Failed - Order #{order.id} Cancelled",
        message=f"Hello {order.user.username},\n\nWe could not process your payment. Your order has been cancelled. Please try checking out again.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.user.email],
        fail_silently=True,
    )        