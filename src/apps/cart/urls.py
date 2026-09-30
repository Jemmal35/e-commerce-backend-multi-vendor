from django.urls import path
from .views import CartView, CartItemDetailView, ApplyCouponView, CheckoutProcessView

urlpatterns = [
    path('', CartView.as_view(), name='cart-detail-add'),
    path('items/<uuid:item_id>/', CartItemDetailView.as_view(), name='cart-item-modify'),
    path('apply-coupon/', ApplyCouponView.as_view(), name='apply-coupon'),
    path('checkout/', CheckoutProcessView.as_view(), name='checkout-process'),
]