from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from core.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from apps.vendors.models import Vendor, VENDOR_STATUS
from apps.vendors.serializers import VendorDetailSerializer
from .serializers import AdminVendorUpdateSerializer

from apps.vendors.tasks import send_vendor_approval_email_task, trigger_vendor_approved_webhook_task

from apps.cart.models import Coupon
from apps.cart.serializers import CouponSerializer

from apps.orders.serializers import DisputeSerializer, AdminDisputeResolutionSerializer
from apps.orders.models import Dispute

from django.db.models import Sum

from apps.orders.models import Order
from apps.catalog.models import Product
from apps.core.models import ActivityLog
from apps.admin_panel.serializers import ActivityLogSerializer

class AdminVendorApplicationListView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        status_filter = request.query_params.get('status')
        queryset = Vendor.objects.select_related('user').all()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        serializer = VendorDetailSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AdminVendorUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def patch(self, request, vendor_id):
        vendor = get_object_or_404(Vendor.objects.select_related('user'), id=vendor_id)

        previous_status = vendor.status

        serializer = AdminVendorUpdateSerializer(vendor, data=request.data, partial=True)
        if serializer.is_valid():
            updated_vendor = serializer.save()
            
            # Handle status changes and role updates
            if previous_status != VENDOR_STATUS.APPROVED and updated_vendor.status == VENDOR_STATUS.APPROVED:
                updated_vendor.user.role = 'vendor'
                updated_vendor.user.save(update_fields=['role'])

                send_vendor_approval_email_task.delay(str(updated_vendor.id))
                trigger_vendor_approved_webhook_task.delay(str(updated_vendor.id))

            elif updated_vendor.status in [VENDOR_STATUS.REJECTED, VENDOR_STATUS.SUSPENDED]:
                if updated_vendor.user.role == 'vendor':
                    updated_vendor.user.role = 'customer'
                    updated_vendor.user.save(update_fields=['role'])

            return Response(
                VendorDetailSerializer(updated_vendor, context={'request': request}).data, 
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CouponListCreateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        coupons = Coupon.objects.all().order_by('-valid_from')
        serializer = CouponSerializer(coupons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CouponDetailAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, id):
        coupon = get_object_or_404(Coupon, id=id)
        serializer = CouponSerializer(coupon)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, id):
        coupon = get_object_or_404(Coupon, id=id)
        serializer = CouponSerializer(coupon, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        coupon = get_object_or_404(Coupon, id=id)
        coupon.delete()
        return Response({"message": "Coupon deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    

class AdminDisputeListView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        dispute = Dispute.objects.select_related('order').all()
        serializer = DisputeSerializer(dispute, many = True)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
class AdminDisputeResolveView(APIView):
    permission_classes  = [IsAdminUser]
    
    def patch(self, request, pk):
        dispute = get_object_or_404(Dispute, id = pk)
        serializer = AdminDisputeResolutionSerializer(dispute, data = request.data, partial = True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    



class AdminPlatformAnalyticsAPIView(APIView):
    """GET /api/v1/admin/analytics/platform/"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        total_revenue = Order.objects.filter(status='PAID').aggregate(
            total=Sum('total_amount')
        )['total'] or 0.00

        data = {
            "platform_gross_revenue": total_revenue,
            "total_orders": Order.objects.count(),
            "total_products": Product.objects.count(),
        }
        return Response(data, status=status.HTTP_200_OK)


class AdminActivityLogListAPIView(APIView):
    """GET /api/v1/admin/audit-logs/"""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        logs = ActivityLog.objects.select_related('actor').all()[:100]
        serializer = ActivityLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)