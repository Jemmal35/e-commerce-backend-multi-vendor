from django.urls import path
from .views import ProductReviewListCreateView


urlpatterns = [
    path('<uuid:product_id>/', ProductReviewListCreateView.as_view(), name='product-reviews'),
]