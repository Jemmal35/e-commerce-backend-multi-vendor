import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.vendors.models import Vendor, VendorAnalyticsSnapshot, VENDOR_STATUS
from apps.core.models import ActivityLog

User = get_user_model()

@pytest.mark.django_db
class TestE2ECommercePipeline:

    def setup_method(self):
        self.client = APIClient()

        # 1. Create Users (Added 'username' to satisfy your User Manager)
        self.admin_user = User.objects.create_superuser(
            username="adminuser",
            email="admin@platform.com", 
            password="adminpassword123"
        )
        self.vendor_user = User.objects.create_user(
            username="vendoruser",
            email="vendor@store.com", 
            password="vendorpassword123"
        )
        self.customer_user = User.objects.create_user(
            username="customeruser",
            email="customer@buyer.com", 
            password="customerpassword123"
        )

        # 2. Create Vendor Profile (Pending initially)
        self.vendor = Vendor.objects.create(
            user=self.vendor_user,
            store_name="Tech Gadgets Store",
            description="Your number one tech store",
            status=VENDOR_STATUS.APPROVED
        )
    def test_full_pipeline_flow(self):
        """
        Tests the complete lifecycle:
        1. Vendor Analytics Dashboard Summary (GET)
        2. Activity Logging Middleware capture on state-changing requests (POST)
        3. Vendor Report Export (Sync & Async checks)
        4. Admin Audit Log Retrieval
        """
        
        # ==========================================
        # STAGE 1: Test Vendor Dashboard Summary API
        # ==========================================
        self.client.force_authenticate(user=self.vendor_user)
        summary_url = reverse('vendor-analytics-summary') # Adjust URL name if needed
        
        response = self.client.get(summary_url)
        assert response.status_code == 200
        data = response.json()
        assert data['store_name'] == "Tech Gadgets Store"
        # Fix the assertion to handle numerical float vs string comparison
        assert float(data['total_revenue']) == 0.0

        # ==========================================
        # STAGE 2: Test Activity Logging Middleware
        # ==========================================
        # Perform a state-changing POST request as the vendor to trigger the middleware
        export_url = reverse('vendor-analytics-export')
        export_payload = {
            "start_date": "2026-01-01",
            "end_date": "2026-01-15"  # 14 days (triggers synchronous CSV stream)
        }
        
        response = self.client.post(export_url, export_payload, format='json')
        assert response.status_code == 200  # Sync CSV download for <= 30 days
        assert 'text/csv' in response['Content-Type']

        # Verify that the ActivityLoggingMiddleware caught this POST request
        log_entry = ActivityLog.objects.filter(path=export_url, method='POST').first()
        assert log_entry is not None
        assert log_entry.actor == self.vendor_user
        assert log_entry.status_code == 200
        assert log_entry.request_payload['start_date'] == "2026-01-01"

        # ==========================================
        # STAGE 3: Test Long-Range Async Export (> 30 days)
        # ==========================================
        long_export_payload = {
            "start_date": "2026-01-01",
            "end_date": "2026-03-15"  # > 30 days (triggers Celery async worker)
        }
        response = self.client.post(export_url, long_export_payload, format='json')
        assert response.status_code == 202  # Accepted for async processing
        assert "task_id" in response.json()

        # ==========================================
        # STAGE 4: Test Admin Audit Log Access
        # ==========================================
        # Switch authentication to Admin User
        self.client.force_authenticate(user=self.admin_user)
        audit_url = reverse('admin-audit-logs')  # Adjust URL name if needed
        
        response = self.client.get(audit_url)
        assert response.status_code == 200
        logs_data = response.json()
        
        # Confirm our previous POST request appears in the admin audit log list
        found = any(log['path'] == export_url and log['method'] == 'POST' for log in logs_data)
        assert found is True

        # ==========================================
        # STAGE 5: Test Admin Platform Analytics
        # ==========================================
        platform_analytics_url = reverse('admin-platform-analytics')
        response = self.client.get(platform_analytics_url)
        assert response.status_code == 200
        platform_data = response.json()
        assert "platform_gross_revenue" in platform_data