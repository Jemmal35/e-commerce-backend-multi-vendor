import random

from rest_framework import serializers
from .models import BulkUploadJob, Product, ProductVariant, Category, ProductImage, ProductStatus
from django.utils.text import slugify

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "parent", "children", "description"]

    def get_children(self, obj):
        if obj.subcategories.exists():
            children = obj.subcategories.all()
            return CategorySerializer(children, many=True).data
        return []
    
    def validate_parent(self, value):
        if self.instance and value and self.instance.id == value.id:
            raise serializers.ValidationError("A category cannot be its own parent.")
        return value
    
    def create(self, validated_data):
        name = validated_data.get("name")
        slug = slugify(name)
        counter = 1
        original_slug = slug
        while Category.objects.filter(slug=slug).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1    
        validated_data["slug"] = slug
        return Category.objects.create(**validated_data)
    
class ProductVariantSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = ProductVariant
        fields = ["id", "attribute", "sku", "price_delta", "stock", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "product", "created_at", "updated_at"]
        
    def validate_attribute(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Attribute must be a dictionary.")
        return value
    
    def validate(self, attrs):
        # Resolve the product from validated_data or context
        product = attrs.get("product") or self.context.get("product")
        attribute = attrs.get("attribute")
        
        if product and attribute:
            # Check if a variant with this exact attribute dictionary already exists for this product
            existing = ProductVariant.objects.filter(product=product, attribute=attribute)
            
            # If we are updating an existing variant, exclude itself from the check
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
                
            if existing.exists():
                raise serializers.ValidationError({
                    "attribute": "A variant with this exact attribute combination already exists for this product."
                })
                
        return attrs
    
    def create(self, validated_data):
        
        product = validated_data.get("product") or self.context.get("product")
        if not product:
            raise serializers.ValidationError({"product": "A variant must be associated with a valid Product."})
        
        validated_data['product'] = product
        
        if not validated_data.get('sku'):
            random_num = random.randint(1000, 9999)
            # Format: ParentSKU-V1234
            validated_data['sku'] = f"{product.sku}-V{random_num}"
            
        return super().create(validated_data)

class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    variants = ProductVariantSerializer(read_only = True, many = True)
    class Meta:
        model = Product
        fields = ["id", "vendor", "vendor_name","category", "category_name", "name", "description", "price", "sku", "stock", "status", "variants","average_rating", "review_count" ,"created_at", "updated_at"]
    
    
class ProductDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.store_name", read_only=True)
    category = CategorySerializer(read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = ["id", "vendor", "vendor_name", "category", "name", "description", "price", "sku", "stock", "status", "variants", "created_at", "updated_at"]
    
    
class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    sku = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Product
        fields = ["id", "category", "name", "description", "price", "sku", "stock", "status"]
        read_only_fields = ["id"]
        
    def validate_price(self, value):
        if value <=0:
            raise serializers.ValidationError("Price must be strictly greater than 0.00.")
        return value
    
    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("Stock quantity cannot be negative.")
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not hasattr(request.user, "vendor_profile"):
            raise serializers.ValidationError({"vendor": "Authenticated user must be an approved vendor to create products."})
        
        vendor = request.user.vendor_profile
        validated_data['vendor'] = vendor
        
        if validated_data.get('stock', 0) == 0 and validated_data.get('status') == ProductStatus.ACTIVE:
            validated_data['status'] = ProductStatus.OUT_OF_STOCK
        
        if not validated_data.get('sku'):
            product_name = validated_data.get('name', 'PRD')
            category = validated_data.get('category')
            category_name = category.name if category else 'CAT'

            # Take the first 3 letters, uppercase them, and pad with 'X' if shorter than 3 letters
            p_prefix = product_name[:3].upper().ljust(3, 'X')
            c_prefix = category_name[:3].upper().ljust(3, 'X')
            random_num = random.randint(10000, 99999)
            
            # Format: PRO-CAT-12345
            validated_data['sku'] = f"{p_prefix}-{c_prefix}-{random_num}"

        product = Product.objects.create(**validated_data)
        return product
    
    
    
    
class BulkUploadJobSerializer(serializers.ModelSerializer):
    error_report_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BulkUploadJob
        fields = [
            'id', 'vendor', 'file', 'error_report', 'status', 'total_rows', 'processed_rows', 'success_count', 'error_count', 'error_report_url', 'created_at', 'updated_at'
        ]
        
    def get_error_report_url(self, obj):
        if obj.error_report:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.error_report.url)
            return obj.error_report.url
        return None