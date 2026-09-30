from rest_framework import serializers

from .models import Order, OrderStatus, OrderItem, Dispute

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source = "product.name", read_only = True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'variant',
            'quantity',
            'unit_price',
            'total_price'
        ]
        
    
class DisputeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Dispute
        fields = [
            'id', 
            'order',
            'reason',
            'description',
            'status',
            'resolution_notes',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'order',
            'status',
            'resolution_notes',
            'created_at'
        ]
        

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many = True, read_only = True)
    dispute = DisputeSerializer(many = True)
    
    class Meta:
        model = Order
        fields = [
            'id',
            'user',
            'vendor',
            'total_amount',
            'shipping_address',
            'status', 
            'created_at',
            'items', 
            'dispute'
        ]
        read_only_fields = fields
        
        
class VendorOrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']
        
        
    def validate_status(self, value):
        allowed_status = [
            OrderStatus.PROCESSING,
            OrderStatus.SHIPPED,
            OrderStatus.DELIVERED
        ]
        
        if value not in allowed_status:
            raise serializers.ValidationError(f"Vendors can only update status to: {','.join(allowed_status)}")
        return value
    

class AdminDisputeResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dispute
        fields = ['status', 'resolution_notes']
        
        