import csv
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status ,permissions

from apps.catalog.models import Product
from apps.core.pagination import StandardResultsSetPagination

from .tasks import generate_vendor_report_csv_async, send_vendor_approval_email_task, trigger_vendor_approved_webhook_task
from .models import Vendor, VENDOR_STATUS, VendorAnalyticsSnapshot
from .serializers import ReportExportRequestSerializer, VendorApplySerilizer, VendorDetailSerializer, VendorProductSerializer
from core.permissions import IsVendorUser, IsAdminUser

from apps.orders.models import Order, OrderStatus, OrderItem, PaymentStatus
from apps.orders.serializers import OrderSerializer, VendorOrderStatusUpdateSerializer

class VendorApplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VendorApplySerilizer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
      
        
class VendorProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendorUser]

    def get(self, request):
        try:
            vendor = Vendor.objects.get(user=request.user)
            serializer = VendorDetailSerializer(vendor)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor profile not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request): 
        vendor_data = request.data
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor profile not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VendorDetailSerializer(vendor, data=vendor_data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @transaction.atomic
    def delete(self, request):
        try:
            vendor = Vendor.objects.get(user=request.user.vendor_profile)
            vendor.delete()
            user = request.user
            if user.role == 'vendor':
                user.role = 'customer'
                user.save(update_fields=['role'])
            return Response({"detail": "Vendor profile deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Vendor.DoesNotExist:
            return Response({"detail": "Vendor profile not found."}, status=status.HTTP_404_NOT_FOUND)


class VendorProductListView(APIView):
    permission_classes = [IsVendorUser]
    
    def get(self, request):
        vendor = get_object_or_404(Vendor, user = request.user)
        
        products = Product.objects.filter(vendor = vendor).prefetch_related('variants').order_by('-created_at')
        paginator = StandardResultsSetPagination()
        paginated_products = paginator.paginate_queryset(products, request, view=self)
        
        serailizer = VendorProductSerializer(paginated_products, many =True)
        
        return paginator.get_paginated_response(serailizer.data)
        
class VendorProductDetailView(APIView):
    permission_classes = [IsVendorUser]
    
    def get(self, request, pk):
        vendor = get_object_or_404(Vendor, user=request.user)
        
        product = get_object_or_404(
            Product.objects.prefetch_related('variants').annotate(
                total_orders_count=Count(
                    'order_items__order',  # <-- Changed from orderitem_set to orderitem
                    filter=Q(order_items__order__payment_status=PaymentStatus.SUCCEEDED),
                    distinct=True
                ),
                total_units_sold=Sum(
                    'order_items__quantity',  # <-- Changed from orderitem_set to orderitem
                    filter=Q(order_items__order__payment_status=PaymentStatus.SUCCEEDED)
                )
            ), 
            pk=pk, 
            vendor=vendor
        )
        
        serializer = VendorProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    
class VendorOrderListView(APIView):
    permission_classes  = [permissions.IsAuthenticated, IsVendorUser]
    
    def get(self, request):
        orders = Order.objects.filter(vendor = request.user.vendor_profile).prefetch_related('items__product')
        serializer = OrderSerializer(orders, many = True)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    
class VendorOrderStatusUpateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendorUser]
    
    def patch(self, request, pk):
        order = get_object_or_404(Order, id = pk, vendor = request.user.vendor_profile)
        serializer = VendorOrderStatusUpdateSerializer(order, data = request.data, partial = True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Order status updated.", "status": serializer.data['status']
            }, status= status.HTTP_200_OK)
            
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    
    
class VendorDashboardSummaryAPIView(APIView):
    """GET /api/v1/vendor/analytics/summary/"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        cache_key = f"vendor_dashboard_summary:{vendor.id}"
        
        # TIP: During testing, you can comment out the cache check 
        # or clear it so you don't see stale data.
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # 1. Fetch snapshots ordered by newest first, capped at 30
        snapshots = VendorAnalyticsSnapshot.objects.filter(vendor=vendor).order_by('-date')[:30]
        
        # 2. Also calculate LIVE metrics for TODAY to ensure real-time orders appear immediately
        today = timezone.localdate()
        today_orders = Order.objects.filter(
            vendor=vendor,
            created_at__date=today,
            payment_status=PaymentStatus.SUCCEEDED  # <-- FIX: Look at payment status, not fulfillment status
        )
        today_aggregates = today_orders.aggregate(
            rev=Sum('total_amount'),
            orders=Count('id')
        )
        today_rev = today_aggregates['rev'] or 0.00
        today_ord_count = today_orders.count()
        today_items = OrderItem.objects.filter(order__in=today_orders).aggregate(total_qty=Sum('quantity'))['total_qty'] or 0
        # 3. Aggregate historical snapshots
        snapshot_totals = snapshots.aggregate(
            rev=Sum('total_revenue'),
            orders=Sum('total_orders'),
            items=Sum('total_items_sold')
        )

        total_revenue = float(snapshot_totals['rev'] or 0.00) + float(today_rev)
        total_orders = (snapshot_totals['orders'] or 0) + today_ord_count
        total_items_sold = (snapshot_totals['items'] or 0) + today_items

        response_data = {
            "vendor_id": str(vendor.id),
            "store_name": vendor.store_name,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_items_sold": total_items_sold,
            "recent_snapshots": [
                {
                    "date": str(s.date),
                    "revenue": float(s.total_revenue),
                    "orders": s.total_orders,
                    "items_sold": s.total_items_sold
                }
                for s in snapshots
            ]
        }

        # Cache response for 15 minutes
        cache.set(cache_key, response_data, timeout=900)
        return Response(response_data, status=status.HTTP_200_OK)


class VendorReportExportAPIView(APIView):
    """POST /api/v1/vendor/analytics/export/"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        vendor = get_object_or_404(Vendor, user=request.user)
        serializer = ReportExportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data['start_date']
        end_date = serializer.validated_data['end_date']
        delta_days = (end_date - start_date).days

        # Sync export for ranges <= 30 days
        if delta_days <= 30:
            snapshots = VendorAnalyticsSnapshot.objects.filter(
                vendor=vendor,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="report_{vendor.slug}_{start_date}_to_{end_date}.csv"'

            writer = csv.writer(response)
            writer.writerow(['Date', 'Total Orders', 'Items Sold', 'Total Revenue'])
            for s in snapshots:
                writer.writerow([s.date, s.total_orders, s.total_items_sold, s.total_revenue])

            return response

        # Async export via Celery for ranges > 30 days
        task = generate_vendor_report_csv_async.delay(
            str(vendor.id),
            str(start_date),
            str(end_date)
        )

        return Response(
            {
                "message": "Report generation initiated for large date range.",
                "task_id": task.id,
                "status": "PROCESSING"
            },
            status=status.HTTP_202_ACCEPTED
        )