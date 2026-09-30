from rest_framework import serializers
from .models import Cart, CartItem, Coupon

from apps.catalog.models import Product, ProductVariant


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_attributes = serializers.JSONField(source='variant.attribute', read_only=True, allow_null=True, default=None  )
    
    unit_price = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()  
    
    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name', 'variant',  
                  'variant_attributes', 'quantity', 'unit_price', 
                  'total_price', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_unit_price(self, obj):
        if obj.variant:
            return obj.variant.price_delta + obj.product.price
        return obj.product.price
    
    def get_total_price(self, obj):
        return self.get_unit_price(obj) * obj.quantity



class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    cart_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'cart_total', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_cart_total(self, obj):
        total = 0
        for item in obj.items.all():
            base_price = item.product.price
            unit_price = base_price + (item.variant.price_delta if item.variant else 0)
            total += unit_price * item.quantity
            
        return total


class CouponSerializer(serializers.ModelSerializer):
    is_valid_now = serializers.BooleanField(source='is_valid', read_only=True)
    
    class Meta:
        model = Coupon
        fields = ['id', 'code', 'discount_type', 'discount_value',
                  'valid_from', 'valid_to', 'usage_limit', 'per_user_limit', 
                  'min_order_value', 'is_valid_now', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']