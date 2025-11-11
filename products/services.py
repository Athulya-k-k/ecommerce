from django.db import models
from .models import Product


class ProductSearchService:
    """
    Service layer for product search operations
    Handles business logic and coordinates between views and models
    """
    
    @staticmethod
    def search_products(filters):
        """
        Main search entry point - applies filters and returns optimized queryset
        
        Args:
            filters: dict with category_id, min_price, max_price
            
        Returns:
            QuerySet of products with category data pre-loaded
        """
        return Product.objects.search_products(**filters)
    
    @staticmethod
    def get_product_detail(product_id):
        """
        Get single product with all related data loaded
        Prevents N+1 queries when accessing category information
        
        Args:
            product_id: ID of product to retrieve
            
        Returns:
            Product instance with category data
        """
        return Product.objects.select_related('category').get(id=product_id)