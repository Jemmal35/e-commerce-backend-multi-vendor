from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response

from django.shortcuts import get_object_or_404

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem
from .models import Review
from .serializers import ReviewSerializer


class ProductReviewListCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        product = get_object_or_404(Product, id = product_id)
        
        reviews = Review.objects.filter(product = product).select_related('user')
        serializer = ReviewSerializer(reviews, many = True)
        
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    
    def post(self, request, product_id):
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required to leave a review."}, status= status.HTTP_400_BAD_REQUEST)
        
        product = get_object_or_404(Product, id = product_id)
        
        if Review.objects.filter(product = product, user = request.user).exists():
            return Response({"error": "You have already reviewed this product."}, status= status.HTTP_400_BAD_REQUEST)
    
        has_perchased = Order.objects.filter(user = request.user, status__in = ['paid', 'processing', 'shipped', 'delivered'], items__product = product).exists()
        
        if not has_perchased:
            return Response({"error": "You can only review products you have purchased and received."}, status= status.HTTP_403_FORBIDDEN)
        
        serializer = ReviewSerializer(data = request.data)
        if serializer.is_valid():
            serializer.save(product = product, user = request.user)
            return Response(serializer.data, status= status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)