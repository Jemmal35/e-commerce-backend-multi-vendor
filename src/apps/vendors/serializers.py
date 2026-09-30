from rest_framework import serializers
from django.utils.text import slugify

from apps.catalog.models import Product, ProductVariant
from .models import VENDOR_STATUS, Vendor

class VendorApplySerilizer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ['id', 'user', 'store_name', 'slug', 'logo', 'description', 'status', 'rejection_reason']
        read_only_fields = ['id', 'user', 'slug', 'status', 'rejection_reason']
        
    def validate(self, attrs):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            if getattr(user, 'role', None) == 'vendor':
                raise serializers.ValidationError("You are already a vendor.")
            
            if Vendor.objects.filter(user=user).exists():
                raise serializers.ValidationError("You have already applied to become a vendor.")
        return attrs
    
    def create(self, validated_data):
        user = self.context['request'].user
        return Vendor.objects.create(user=user, 
                                     status=VENDOR_STATUS.PENDING,
                                     **validated_data)
  
class VendorProductVariantReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ["id", "attribute", "sku", "price_delta", "stock", "is_active", "created_at", "updated_at"]
        read_only_fields = fields
  
  
class VendorProductSerializer(serializers.ModelSerializer):
    variants = VendorProductVariantReadSerializer(many = True, read_only = True)
    
    total_orders_count = serializers.IntegerField(read_only = True, default = 0)
    total_units_sold = serializers.IntegerField(read_only = True, default = 0)
    class Meta:
        model = Product
        fields = [
            'id', 
            'name', 
            'description', 
            'price', 
            'stock',
            'sku',
            'status', 
            'category',
            'average_rating' ,
            'review_count',
            'total_orders_count',
            'total_units_sold',
            'variants', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = fields    


class VendorDetailSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = Vendor
        fields = ['id', 'user', 'store_name', 'slug', 'logo', 'description', 'status', 'rejection_reason', 'user_email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'slug', 'status', 'rejection_reason', 'user_email', 'created_at', 'updated_at']
        
        
    def validate_store_name(self, value):
        query = Vendor.objects.filter(store_name__iexact=value)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
            
        if query.exists():
            raise serializers.ValidationError("Store name already exists.")
    
        return value
    
    def update(self, instance, validated_data):
        new_store_name = validated_data.get('store_name')
        if new_store_name and new_store_name != instance.store_name:
            base_slug = slugify(new_store_name)
            unique_slug = base_slug
            counter = 1

            while Vendor.objects.filter(slug=unique_slug).exclude(pk=instance.pk).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = unique_slug
            
        return super().update(instance, validated_data)
    
    
class ReportExportRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("start_date must be before or equal to end_date.")
        return data    
