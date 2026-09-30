from django.urls import path, include
from .views import (
    BulkUploadCreateView,
    CategoryListCreateView,
    CategoryDetailView,
    ProductListCreateView,
    ProductDetailView,
    ProductVariantListCreateView,
    ProductVariantDetailView,
    ProductImageUploadView,
    BulkUploadStatusView
)

urlpatterns = [
    path('categories/', CategoryListCreateView.as_view(), name= 'category-list-create'),
    path('categories/<uuid:id>/', CategoryDetailView.as_view(), name= 'category-detail'),
    
    path('products/', ProductListCreateView.as_view(), name= 'product-list-create'),
    path('products/<uuid:id>/', ProductDetailView.as_view(), name= 'product-detail'),
    path('products/<uuid:product_id>/images/', ProductImageUploadView.as_view(), name= 'product-image-upload'),

    path('products/<uuid:product_id>/variants/', ProductVariantListCreateView.as_view(), name= 'variant-list-create'),
    path('products/<uuid:product_id>/variants/<uuid:id>/', ProductVariantDetailView.as_view(), name= 'variant-detail'),

    path('bulk-upload/', BulkUploadCreateView.as_view(), name='bulk-upload-create'),
    path('bulk-upload/<uuid:job_id>/status/', BulkUploadStatusView.as_view(), name='bulk-upload-status'),
    path('reviews/', include('apps.reviews.urls'))
    
]
