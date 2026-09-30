from django.urls import path
from .views import( AdminActivityLogListAPIView, AdminPlatformAnalyticsAPIView, AdminVendorUpdateView, AdminVendorApplicationListView, CouponDetailAPIView, CouponListCreateAPIView,
                   AdminDisputeListView, AdminDisputeResolveView, )


urlpatterns = [
    path('vendors/', AdminVendorApplicationListView.as_view(), name='admin-vendor-list'),
    path('vendors/<uuid:vendor_id>/status/', AdminVendorUpdateView.as_view(), name='admin-vendor-update'),
    path('coupons/', CouponListCreateAPIView.as_view(), name='coupon-list-create'),
    path('coupons/<uuid:id>/', CouponDetailAPIView.as_view(), name='coupon-detail'),
    path('disputes/', AdminDisputeListView.as_view(), name='admin-dispute-list'),
    path('disputes/<uuid:pk>/resolve/', AdminDisputeResolveView.as_view(), name='admin-dispute-resolve'),
    path('analytics/platform/', AdminPlatformAnalyticsAPIView.as_view(), name='admin-platform-analytics'),
    path('audit-logs/', AdminActivityLogListAPIView.as_view(), name='admin-audit-logs'),
]