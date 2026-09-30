from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import Q, QuerySet
from .models import Product, Category, ProductStatus
from django.db import connection

class ProductSearchEngine:
    
    @staticmethod
    def execute(
        query_text: str = None,
        category_id: str = None,
        vendor_id: str = None,
        status: str = None,
        min_price: float = None,
        max_price: float = None,
        base_queryset: QuerySet = None,
        )-> QuerySet:
        
        if base_queryset is None:
            base_queryset = Product.objects.select_related("category", "vendor").all()
        
        qs = base_queryset
        
        if status:
            qs = qs.filter(status=status)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)
        if min_price is not None:
            qs = qs.filter(price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(price__lte=max_price)

        # if query_text and query_text.strip():
            
        #     vector = (SearchVector("name", weight="A") + 
        #                 SearchVector("description", weight="B") + 
        #                 SearchVector("category__name", weight="C") + 
        #                 SearchVector("vendor__store_name", weight="D")
        #     )
        #     search_query = SearchQuery(query_text.strip(), search_type="websearch")

        #     qs = qs.annotate(rank=SearchRank(vector, search_query)).filter(rank__gte=0.1).order_by("-rank")
        if query_text and query_text.strip():
            clean_query = query_text.strip()
    
            # Check if running on SQLite (local dev) vs PostgreSQL (production)
            if connection.vendor == 'sqlite':
                # SQLite-compatible fallback using icontains
                qs = qs.filter(
                    Q(name__icontains=clean_query) |
                    Q(description__icontains=clean_query) |
                    Q(category__name__icontains=clean_query) |
                    Q(vendor__store_name__icontains=clean_query)
                ).distinct()
            else:
                # PostgreSQL Full-Text Search with ranking
                vector = (
                    SearchVector("name", weight="A") + 
                    SearchVector("description", weight="B") + 
                    SearchVector("category__name", weight="C") + 
                    SearchVector("vendor__store_name", weight="D")
                )
                search_query = SearchQuery(clean_query, search_type="websearch")
                qs = qs.annotate(rank=SearchRank(vector, search_query)).filter(rank__gte=0.1).order_by("-rank")
        else:
            qs = qs.order_by("-created_at")
            
        return qs