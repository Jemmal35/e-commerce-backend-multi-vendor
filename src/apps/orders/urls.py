from django.urls import path

from apps.orders.views import CheckoutOrderView, CustomerOrderListView, CustomerOrderDetailView, RaiseDisputeView

urlpatterns = [
    path('checkout/', CheckoutOrderView.as_view(), name='checkout-order'),
    path('', CustomerOrderListView.as_view(), name='customer-order-list'),
    path('<uuid:pk>/', CustomerOrderDetailView.as_view(), name='customer-order-detail'),
    path('<uuid:pk>/dispute/', RaiseDisputeView.as_view(), name='raise-dispute')
]