from rest_framework.views import APIView
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from apps.core.pagination import StandardResultsSetPagination

from .models import Category, Product, ProductVariant, ProductImage, BulkUploadJob, BulkUploadStatus
from .serializers import (CategorySerializer, 
                          ProductListSerializer, 
                          ProductDetailSerializer, 
                          ProductVariantSerializer, 
                          ProductCreateUpdateSerializer,
                          BulkUploadJobSerializer,
                          )
from .search import ProductSearchEngine
from .tasks import process_bulk_upload

from core.permissions import (
    IsAdminUser,
    IsCustomerUser,
    IsVendorUser,
    IsVendorOwnerOrReadOnly,
)

class CategoryListCreateView(APIView):
    permission_classes = [IsAdminUser] 
    
    def get_permissions(self):
        # Allow public access for GET requests
        if self.request.method == 'GET':
            return [] 
        return super().get_permissions()
    
    def get(self, request):
        categories = Category.objects.filter(parent__isnull = True)
        
        paginator = StandardResultsSetPagination()
        paginated_categories = paginator.paginate_queryset(categories, request, view= self)
        serializer = CategorySerializer(paginated_categories, many = True)
        
        return paginator.get_paginated_response(serializer.data)
    
    
    def post(self, request):
        serializer = CategorySerializer(data = request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_201_CREATED)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    
class CategoryDetailView(APIView):
    permission_classes = [IsAdminUser] 
    def get_permissions(self):
            # Allow public access for GET requests
            if self.request.method == 'GET':
                return [] 
            return super().get_permissions()
        
    def get_object(self, id):
        return get_object_or_404(Category, pk = id)
    
    def get(self, request, id):
        category = self.get_object(id)
        serializer = CategorySerializer(category)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    def put(self, request, id):
        category = self.get_object(id)
        serializer = CategorySerializer(category, data= request.data, partial = True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_200_OK)
        return Response(serializer.errors,status= status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, id):
        category = self.get_object(id)
        category.delete()
        return Response({"detail":"Category deleted successfully."}, status= status.HTTP_204_NO_CONTENT)
    
    

class ProductListCreateView(APIView):
    
    permission_classes  = [IsVendorOwnerOrReadOnly]
    
    def get(self, request):
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        query_text = request.query_params.get('q')
        category_id = request.query_params.get('category')
        vendor_id = request.query_params.get('vendor')
        
        queryset = ProductSearchEngine.execute(
            query_text=query_text,
            category_id=category_id,
            vendor_id=vendor_id,
            status= 'active',
            min_price= float(min_price) if min_price else None,
            max_price= float(max_price) if max_price else None,            
        )
        
        paginator = StandardResultsSetPagination()
        paginated_products = paginator.paginate_queryset(queryset, request, view=self)
        
        serializer = ProductListSerializer(paginated_products, many= True)
        return paginator.get_paginated_response(serializer.data)
             
        
    def post(self, request):
        serializer = ProductCreateUpdateSerializer(data = request.data, context = {'request':request})
        if serializer.is_valid():
            serializer.save()
            serilialized_detail = ProductDetailSerializer(serializer.instance)
            return Response(serilialized_detail.data, status= status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class ProductDetailView(APIView):
    permission_classes  = [IsVendorOwnerOrReadOnly]
    
    def get_object(self, id):
        product = get_object_or_404(Product, pk = id)
        self.check_object_permissions(self.request, product)
        return product
    
    def get(self, request, id):
        product = self.get_object(id)
        serializer = ProductDetailSerializer(product)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    def put(self, request, id):
        product = self.get_object(id)
        serializer = ProductCreateUpdateSerializer(product, data = request.data, partial = True)
        if serializer.is_valid():
            serializer.save()
            serilialized_detail = ProductDetailSerializer(serializer)
            return Response(serilialized_detail.data, status= status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    def delete(self, request, id):
        product = self.get_object(id)
        
        if not hasattr(request.user, 'vendor_profile') or product.vendor != request.user.vendor_profile:
            return Response({"detail": "You do not own this product."}, status=status.HTTP_403_FORBIDDEN)
        product.delete()
        
        return Response({"detail":"Product deleted successfully."}, status= status.HTTP_204_NO_CONTENT)
    

class ProductVariantListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get(self, request, product_id):
        variants = ProductVariant.objects.filter(product_id = product_id)
        serializer = ProductVariantSerializer(variants, many = True )
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk = product_id)
        if not hasattr(request.user, 'vendor_profile') or product.vendor != request.user.vendor_profile:
            return Response({"detail": " You do not own this product."}, status= status.HTTP_403_FORBIDDEN)
        
        is_many = isinstance(request.data, list)
        
        serializer = ProductVariantSerializer(
            data=request.data, 
            context={'product': product},
            many=is_many # Dynamically set many=True if it's a list
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status= status.HTTP_201_CREATED)
        return Response(serializer.errors, status= status.HTTP_400_BAD_REQUEST)
    
    
class ProductVariantDetailView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_object(self, product_id, id):
        return get_object_or_404(ProductVariant, product_id = product_id, pk = id)
    
    def get(self, request, product_id, id):
        variant = self.get_object(product_id, id)
        serializer = ProductVariantSerializer(variant)
        return Response(serializer.data, status= status.HTTP_200_OK)
    
    
    def put(self, request, product_id, id):
        variant = self.get_object(product_id, id)
        if not hasattr(request.user, 'vendor_profile') or variant.product.vendor != request.user.vendor_profile:
                    return Response({"detail": " You do not own this product."}, status= status.HTTP_403_FORBIDDEN)
        
        serializer = ProductVariantSerializer(variant, data = request.data, partial = True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status= status.HTTP_200_OK)
        return Response(serializer.errors,status= status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, product_id, id):
        variant = self.get_object(product_id, id)
        if not hasattr(request.user, 'vendor_profile') or variant.product.vendor != request.user.vendor_profile:
                    return Response({"detail": " You do not own this product."}, status= status.HTTP_403_FORBIDDEN)
        variant.delete()
        return Response({"detail": f"The variant for {variant.product.name} is removed successfully."}, status= status.HTTP_204_NO_CONTENT)
            

class ProductImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        
        if not hasattr(request.user, 'vendor_profile') or product.vendor != request.user.vendor_profile:
            return Response({"detail": "You do not own this product."}, status=status.HTTP_403_FORBIDDEN)

        # Use getlist() to retrieve an array of files sent under the 'images' key
        images = request.FILES.getlist('images')
        if not images:
            return Response({"images": "No image files provided. Use the 'images' key."}, status=status.HTTP_400_BAD_REQUEST)
        
        is_featured = request.data.get('is_featured', 'false').lower() == 'true'
        created_images = []
        
        for img in images:
            product_image = ProductImage.objects.create(
                product=product, 
                image=img, 
                is_featured=is_featured
            )
            created_images.append({
                "id": str(product_image.id),
                "image_url": product_image.image.url if hasattr(product_image.image, 'url') else None,
                "is_featured": product_image.is_featured
            })
            # Ensure only the first image gets the 'featured' flag if uploading in bulk
            is_featured = False 

        return Response(created_images, status=status.HTTP_201_CREATED)
    
    
    
class BulkUploadCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendorUser]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        if not hasattr(request.user, 'vendor_profile') or request.user.vendor_profile.status != 'approved':
            return Response({"detail": "An approved vendor profile is required."}, status=status.HTTP_403_FORBIDDEN)
        
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"file": "No CSV file provided."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_obj.name.endswith('.csv'):
            return Response({"file": "Invalid format. Only CSV files are supported."}, status=status.HTTP_400_BAD_REQUEST)
        
        job = BulkUploadJob.objects.create(
            vendor = request.user.vendor_profile,
            file = file_obj
        )
        
        process_bulk_upload.delay(str(job.id))
        serializer = BulkUploadJobSerializer(job, context = {'request': request})
        return Response(serializer.data, status= status.HTTP_202_ACCEPTED)
    

class BulkUploadStatusView(APIView):
    permission_classes = [IsVendorUser]
    
    def get(self, request, job_id):
        job = get_object_or_404(BulkUploadJob, pk = job_id)
    
        if request.user.role != 'admin' and (not hasattr(request.user, 'vendor_profile') or job.vendor != request.user.vendor_profile):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BulkUploadJobSerializer(job, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)