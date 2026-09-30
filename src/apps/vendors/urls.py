from django.urls import path
from .views import (VendorApplyView, VendorDashboardSummaryAPIView, VendorProfileView, VendorOrderListView, 
                    VendorOrderStatusUpateView, VendorReportExportAPIView, VendorProductListView, VendorProductDetailView)


urlpatterns = [
    path('apply/', VendorApplyView.as_view(), name='vendor-apply'),
    path('me/', VendorProfileView.as_view(), name='vendor-profile'),
    path('orders/', VendorOrderListView.as_view(), name='vendor-order-list'),
    path('orders/<uuid:pk>/status/', VendorOrderStatusUpateView.as_view(), name='vendor-order-status-update'),
    path('analytics/summary/', VendorDashboardSummaryAPIView.as_view(), name='vendor-analytics-summary'),
    path('analytics/export/', VendorReportExportAPIView.as_view(), name='vendor-analytics-export'),
    path('products/', VendorProductListView.as_view(), name= 'vendor-product-list'),
    path('products/<uuid:pk>/', VendorProductDetailView.as_view(), name= 'vendor-product-detail'),
    
]
    