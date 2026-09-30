from decimal import Decimal
from collections import defaultdict

from django.core.cache import cache
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Order, OrderItem, OrderStatus
from apps.cart.models import Cart, Coupon
from apps.catalog.models import Product, ProductVariant
from apps.payments.services import PaymentService

from .serializers import DisputeSerializer, OrderItemSerializer, VendorOrderStatusUpdateSerializer, OrderSerializer

IDEMPOTENCY_PROCESSING_TTL = 60 
INDEMPOTENCY_RESPONSE_TTL = 86400


class CheckoutOrderView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        idempotency_key = request.headers.get('X-Idempotency-Key') or request.data.get('Idempotency-Key')
        if not idempotency_key:
            return Response({"error": "Idempotency key is required for checkout."}, status=status.HTTP_400_BAD_REQUEST)
        
        cache_key = f"indempotency:{request.user.id}:{idempotency_key.strip()}"
        cached_record = cache.get(cache_key)
        
        if cached_record:
            if cached_record.get('status') == 'processing':
                return Response(
                    {"error": "A checkout request with this idempotency key is already being processed. Please wait."}, 
                    status=status.HTTP_409_CONFLICT
                )
            return Response(cached_record.get('data'), status=cached_record.get('status_code', status.HTTP_200_OK))
        
        if not cache.add(cache_key, {'status': 'processing'}, timeout=IDEMPOTENCY_PROCESSING_TTL):
            return Response(
                {"error": "A checkout request with this idempotency key is already being processed. Please wait."}, 
                status=status.HTTP_409_CONFLICT
            )
        
        shipping_address = request.data.get('shipping_address')
        coupon_code = str(request.data.get('coupon_code', '')).strip()
        
        if not shipping_address or not isinstance(shipping_address, dict):
            cache.delete(cache_key)
            return Response({"error": "A valid shipping_address object is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Wrap entire checkout sequence in an atomic transaction
            with transaction.atomic():
                cart = get_object_or_404(
                    Cart.objects.prefetch_related('items__product__vendor', 'items__variant'), 
                    user=request.user
                )

                if not cart.items.exists():
                    cache.delete(cache_key)
                    return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
                
                coupon = None
                if coupon_code:
                    try:
                        coupon = Coupon.objects.get(code=coupon_code)
                        if not coupon.is_valid():
                            cache.delete(cache_key)
                            return Response({"error": "Invalid or expired coupon."}, status=status.HTTP_400_BAD_REQUEST)
                    except Coupon.DoesNotExist:
                        cache.delete(cache_key)
                        return Response({"error": "Coupon does not exist."}, status=status.HTTP_400_BAD_REQUEST)

                product_ids = [item.product.id for item in cart.items.all()]
                variant_ids = [item.variant.id for item in cart.items.all() if item.variant]
                
                # Locks row for update within the transaction
                locked_products = {
                    p.id: p for p in Product.objects.filter(id__in=product_ids).select_for_update()
                }
                locked_variants = {
                    v.id: v for v in ProductVariant.objects.filter(id__in=variant_ids).select_for_update()
                }

                vendor_items_map = defaultdict(list)
                for item in cart.items.all():
                    product = locked_products.get(item.product.id)
                    variant = locked_variants.get(item.variant.id) if item.variant else None
                    
                    available_stock = variant.stock if variant else product.stock
                    if available_stock < item.quantity:
                        cache.delete(cache_key)
                        return Response(
                            {"error": f"Insufficient stock for {product.name}. Available: {available_stock}"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    unit_price = (product.price + variant.price_delta) if variant else product.price
                    total_price = unit_price * item.quantity
                    
                    vendor_items_map[product.vendor].append({
                        'item': item,
                        'product': product,
                        'variant': variant,
                        'unit_price': unit_price,
                        'total_price': total_price
                    })

                created_orders = []
            
                for vendor, items in vendor_items_map.items():
                    vendor_order_total = sum(item['total_price'] for item in items)
                    
                    if coupon and coupon.is_valid():              
                        if coupon.discount_type == Coupon.DiscountType.PERCENTAGE:
                            discount_amount = (vendor_order_total * coupon.discount_value) / Decimal('100.00')
                        elif coupon.discount_type == Coupon.DiscountType.FIXED_AMOUNT:
                            discount_amount = min(coupon.discount_value, vendor_order_total)
                        else:
                            discount_amount = Decimal('0.00')
                        
                        vendor_order_total -= discount_amount

                    order = Order.objects.create(
                        user=request.user,
                        vendor=vendor,
                        coupon=coupon,
                        total_amount=vendor_order_total,
                        shipping_address=shipping_address,  # Saved address snapshot
                        status=OrderStatus.PENDING
                    )
                    
                    for data in items:
                        item = data['item']
                        product = data['product']
                        variant = data['variant']
                        
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            variant=variant,
                            quantity=item.quantity,
                            unit_price=data['unit_price'],
                            total_price=data['total_price']
                        )
                        
                        if variant:
                            variant.stock -= item.quantity
                            variant.save(update_fields=['stock'])
                        else:
                            product.stock -= item.quantity
                            product.save(update_fields=['stock'])
                
                    created_orders.append(order)
                payment_data = PaymentService.initialize_checkout_payment(
                    orders=created_orders,
                    user_email=request.user.email
                    )
                # Empty the user's cart
                cart.items.all().delete()
            
            # Formulate response outside transaction block once committed
            response_payload = {
                "message": "Checkout initiated successfully.",
                "idempotency_key": idempotency_key,
                "client_secret": payment_data["client_secret"],
                "payment_intent_id": payment_data["payment_intent_id"],
                "grand_total": str(payment_data["grand_total"]),
                "orders": [
                    {
                        "id": str(o.id),
                        "vendor_id": str(o.vendor_id),
                        "total_amount": str(o.total_amount),
                        "status": o.status
                    } for o in created_orders
                ]
}
            
            cache.set(
                cache_key, 
                {'status': 'completed', 'data': response_payload, 'status_code': status.HTTP_201_CREATED}, 
                timeout=INDEMPOTENCY_RESPONSE_TTL
            )
            
            return Response(response_payload, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            cache.delete(cache_key)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
        
class CustomerOrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        orders = Order.objects.filter(user = request.user).prefetch_related('items__product')
        serializer = OrderSerializer(orders, many = True)
        return Response(serializer.data, status= status.HTTP_200_OK)
        

class CustomerOrderDetailView(APIView):
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        order = get_object_or_404(Order, id = pk, user = request.user)
        serialier = OrderSerializer(order)
        return Response(serialier.data, status= status.HTTP_200_OK)
    
    
class RaiseDisputeView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        order = get_object_or_404(Order, id = pk, user = request.user)
        
        if hasattr(order, 'dispute'):
            return Response({
                "error": "A dispute already exists for this order."
            }, status= status.HTTP_400_BAD_REQUEST)
            
        serializer = DisputeSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_201_CREATED)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)