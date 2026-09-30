from decimal import Decimal

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Cart, CartItem, Coupon, CouponUsage, DiscountType

from .serializers import CartSerializer, CartItemSerializer, CouponSerializer

from apps.catalog.models import Product, ProductVariant

from django.shortcuts import get_object_or_404

class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, created = Cart.objects.prefetch_related('items__product', 'items__variant').get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        product_id = request.data.get('product')
        variant_id = request.data.get('variant', None)
        
        try:
            quantity = int(request.data.get('quantity', 1))
        except (ValueError, TypeError):
            return Response({"error": "Invalid quantity provided."}, status=status.HTTP_400_BAD_REQUEST)

        if quantity < 1:
            return Response({"error": f"Quantity must be at least 1."}, status=status.HTTP_400_BAD_REQUEST)
        
        product = get_object_or_404(Product, id=product_id)
        variant = None
        
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id, product=product)
            if not variant.stock or variant.stock < quantity:
                return Response({"error": "Insufficient stock for the selected variant."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if not product.stock or product.stock < quantity:
                return Response({"error": f"Insufficient stock for the selected product. Available: {product.stock}"}, status=status.HTTP_400_BAD_REQUEST)
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product, variant=variant, defaults={'quantity': quantity})
        
        if not created:
            new_total_qty = cart_item.quantity + quantity
            available_stock = variant.stock if variant else product.stock
            
            if available_stock < new_total_qty:
                return Response({"error": f"Cannot add more. Total would exceed available stock ({available_stock})."}, status=status.HTTP_400_BAD_REQUEST)
            cart_item.quantity = new_total_qty
            cart_item.save()
            
        serializer = CartSerializer(cart)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    
class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        new_quantity = request.data.get('quantity', 0)
        
        if new_quantity < 1:
            cart_item.delete()
        else:
            available_stock = cart_item.variant.stock if cart_item.variant else cart_item.product.stock
            
            if available_stock < new_quantity:
                return Response({"error": f"Insufficient stock. Available: {available_stock}"}, status=status.HTTP_400_BAD_REQUEST)
            
            cart_item.quantity = new_quantity
            cart_item.save()
        
        serializer = CartItemSerializer(cart_item)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        serializer = CartSerializer(cart)
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)
    

class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        coupon_code = request.data.get('coupon_code', '').strip()
        
        if not coupon_code:
            return Response({"error": "Coupon code is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            coupon = Coupon.objects.get(code=coupon_code)
        except Coupon.DoesNotExist:
            return Response({"error": "Invalid coupon code."}, status=status.HTTP_404_NOT_FOUND)
        
        if not coupon.is_valid:
            return Response({"error": "This coupon is not valid at the moment."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check usage limits
        total_usage_count = CouponUsage.objects.filter(coupon=coupon).count()
        if coupon.usage_limit and total_usage_count >= coupon.usage_limit:
            return Response({"error": "This coupon has reached its maximum usage limit."}, status=status.HTTP_400_BAD_REQUEST)

        user_usage_count = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
        if coupon.per_user_limit and user_usage_count >= coupon.per_user_limit:
            return Response({"error": "You have reached the maximum usage limit for this coupon."}, status=status.HTTP_400_BAD_REQUEST)

        # Check minimum order value
        cart = get_object_or_404(Cart.objects.prefetch_related('items__product', 'items__variant'), user=request.user)
        
        subtotal = Decimal('0.00')
        for item in cart.items.all():
            base_price = item.product.price
            unit_price = base_price + (item.variant.price_delta if item.variant else 0)
            subtotal += unit_price * item.quantity
        
        if subtotal == 0:
            return Response({"error": "Cannot apply a coupon to an empty cart."}, status=status.HTTP_400_BAD_REQUEST)
        
        if coupon.min_order_value and subtotal < coupon.min_order_value:
            return Response({"error": f"Cart total must be at least {coupon.min_order_value} to apply this coupon."}, status=status.HTTP_400_BAD_REQUEST)

        discount_amount = Decimal('0.00')
        if coupon.discount_type == DiscountType.PERCENTAGE:
            discount_amount = (subtotal * coupon.discount_value) / Decimal('100.00')
        elif coupon.discount_type == DiscountType.FIXED_AMOUNT:
            discount_amount = coupon.discount_value
            
            if discount_amount > subtotal:
                discount_amount = subtotal  # Ensure discount doesn't exceed subtotal
        
        final_total = subtotal - discount_amount
        if final_total < 0:
            final_total = Decimal('0.00')  # Ensure final total doesn't go negative

        return Response({
            "message": "Coupon applied successfully.",
            "code": coupon.code,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "final_total": final_total
        }, status=status.HTTP_200_OK)
        
        
class CheckoutProcessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            with transaction.atomic():
                cart = get_object_or_404(Cart.objects.prefetch_related('items__product', 'items__variant'), user=request.user)
                
                if not cart.items.exists():
                    return Response({"error": "Your cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
                
                product_ids = [item.product.id for item in cart.items.all()]
                variant_ids = [item.variant.id for item in cart.items.all() if item.variant]
                
                locked_products = {
                    p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
                }
                locked_variants = {
                    v.id: v for v in ProductVariant.objects.select_for_update().filter(id__in=variant_ids)
                }
                
                for item in cart.items.all():
                    product = locked_products[item.product.id]
                    variant = locked_variants.get(item.variant.id) if item.variant else None
                    
                    available_stock = variant.stock if variant else product.stock
                    
                    if available_stock < item.quantity:
                        name = variant.attribute if variant else product.name
                        return Response({
                            "error": f"Stock level changed for '{name}'. Only {available_stock} remaining."
                        }, status=status.HTTP_400_BAD_REQUEST)
                    

                return Response({
                    "message": "Stock re-validated successfully with row-level locking. Ready for order creation."
                }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)