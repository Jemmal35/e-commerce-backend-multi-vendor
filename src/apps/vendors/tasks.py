import logging
import requests
from django.conf import settings
from celery import shared_task
from .models import Vendor
import csv
import io
from datetime import date, timedelta
from celery import shared_task
from django.db.models import Sum, Count
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import VendorAnalyticsSnapshot
from apps.vendors.models import Vendor, VENDOR_STATUS
from apps.orders.models import Order, OrderItem, PaymentStatus

from django.core.mail import send_mail


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_vendor_approval_email_task(self, vendor_id):
    try:
        vendor = Vendor.objects.select_related('user').get(id=vendor_id)
        subject = "Vendor Application Approved"
        message = (f"Hello {vendor.user.first_name or vendor.user.username},\n\n"
            f"Great news! Your vendor application for '{vendor.store_name}' has been approved.\n"
            "You can now access your vendor dashboard and begin adding products.\n\n"
            "Best regards,\nMarketplace Team")
        recipient_list = [vendor.user.email]
        
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list, fail_silently=False)
        logger.info(f"Approval email sent to {vendor.user.email} for vendor {vendor.store_name}.")
    except Vendor.DoesNotExist:
        logger.error(f"Vendor with ID {vendor_id} does not exist.")
    except Exception as e:
        logger.error(f"Error sending approval email for vendor ID {vendor_id}: {str(e)}")
        self.retry(exc=e)
        
@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def trigger_vendor_approved_webhook_task(self, vendor_id):
    try:
        vendor = Vendor.objects.select_related('user').get(id=vendor_id)
        webhook_url = getattr(settings, 'VENDOR_APPROVAL_WEBHOOK_URL', None)
        
        payload = {
            "event": "vendor_approved",
            "vendor_id": str(vendor.id),
            "store_name": vendor.store_name,
            "slug": vendor.slug,
            "user_email": vendor.user.email,
        }
        if webhook_url:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Webhook triggered for vendor {vendor.store_name} with status {vendor.status}.")
    except Vendor.DoesNotExist:
        logger.error(f"Vendor with ID {vendor_id} does not exist.")
    except requests.RequestException as e:
        logger.error(f"Error triggering webhook for vendor ID {vendor_id}: {str(e)}")
        self.retry(exc=e)
        
        
    

@shared_task
def generate_nightly_vendor_snapshots():
    """
    Celery Beat job: Summarizes yesterday's metrics for all APPROVED vendors.
    """
    target_date = date.today() - timedelta(days=1)
    approved_vendors = Vendor.objects.filter(status=VENDOR_STATUS.APPROVED)

    for vendor in approved_vendors:
        orders = Order.objects.filter(
            vendor=vendor,
            created_at__date=target_date,
            payment_status=PaymentStatus.SUCCEEDED  # <-- FIX HERE TOO
        )
        
        aggregates = orders.aggregate(
            total_rev=Sum('total_amount'),
            total_ord=Count('id')
        )
        
        items_sold = OrderItem.objects.filter(
            order__in=orders
        ).aggregate(total_qty=Sum('quantity'))['total_qty'] or 0

        VendorAnalyticsSnapshot.objects.update_or_create(
            vendor=vendor,
            date=target_date,
            defaults={
                'total_revenue': aggregates['total_rev'] or 0.00,
                'total_orders': aggregates['total_ord'] or 0,
                'total_items_sold': items_sold,
            }
        )


@shared_task
def generate_vendor_report_csv_async(vendor_id, start_date_str, end_date_str):
    """
    Async report generation using Vendor UUID.
    """
    vendor = Vendor.objects.get(id=vendor_id)
    snapshots = VendorAnalyticsSnapshot.objects.filter(
        vendor=vendor,
        date__gte=start_date_str,
        date__lte=end_date_str
    ).order_by('date')

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Total Orders', 'Items Sold', 'Total Revenue ($)'])

    for s in snapshots:
        writer.writerow([s.date, s.total_orders, s.total_items_sold, s.total_revenue])

    filename = f"reports/vendor_{vendor.id}_{start_date_str}_to_{end_date_str}.csv"
    file_path = default_storage.save(filename, ContentFile(output.getvalue().encode('utf-8')))
    return file_path