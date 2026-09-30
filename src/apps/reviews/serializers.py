from rest_framework import serializers

from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only = True)
    product_name = serializers.CharField(source = 'product.name', read_only = True)
    
    class Meta:
        model = Review
        fields = [
            'id',
            'user',
            'product_name',
            'rating',
            'comment',
            'created_at'
        ]
        read_only_fields = [
            'id', 'created_at'
        ]
        
        def validate_rating(self, value):
            if not (1<= value <= 5):
                raise serializers.ValidationError("Rating must be an integer between 1 and 5.")
            return value