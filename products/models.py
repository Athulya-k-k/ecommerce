from django.db import models
from django.utils import timezone


class Category(models.Model):
    """Simple category model for organizing products"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['is_active', 'name'], name='idx_category_active_name'),
        ]
    
    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    """Custom queryset for product filtering operations"""
    
    def active_products(self):
        """Return only active products"""
        return self.filter(is_active=True)
    
    def by_category(self, category_id):
        """Filter by specific category"""
        return self.filter(category_id=category_id)
    
    def by_price_range(self, min_price, max_price):
        """Filter products within price range"""
        return self.filter(price__range=(min_price, max_price))
    
    def search_products(self, category_id=None, min_price=None, max_price=None):
        """
        Main search method that combines common filters
        Used for category browsing and product discovery
        """
        # Start with active products only
        queryset = self.active_products()
        
        # Apply category filter if provided
        if category_id:
            queryset = queryset.by_category(category_id)
        
        # Apply price range if both min and max are provided
        if min_price is not None and max_price is not None:
            queryset = queryset.by_price_range(min_price, max_price)
        
        # Optimize query by including category data and applying default ordering
        return queryset.select_related('category').order_by('-created_at')


class ProductManager(models.Manager):
    """Custom manager for Product model with common query methods"""
    
    def get_queryset(self):
        return ProductQuerySet(self.model, using=self._db)
    
    def active_products(self):
        return self.get_queryset().active_products()
    
    def search_products(self, **filters):
        return self.get_queryset().search_products(**filters)


from django.db import models
from django.utils import timezone


class Product(models.Model):
    """
    Core product model for e-commerce catalog
    Includes optimized indexing for common search patterns
    """
    sku = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique product identifier"
    )
    name = models.CharField(
        max_length=200,
        help_text="Product display name"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Product price in USD"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether product is available for sale"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        help_text="Product category"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When product was added to catalog"
    )
    description = models.TextField(blank=True)
    
    objects = ProductManager()
    
    class Meta:
        ordering = ['-created_at']
        
        # =========================================================================
        # INDEXING STRATEGY - Optimized for different search scenarios:
        #
        # PRIMARY INDEXES:
        # - [is_active, category, -created_at] for category browsing (no price filter)
        # - [is_active, category, price, -created_at] for filtered searches (with price)
        # - Database query planner chooses the best one automatically
        #
        # SECONDARY INDEX: [is_active, price]  
        # - For price-only searches across all categories
        # - Handles "deals under $X" type queries
        #
        # UTILITY INDEXES: sku and name for direct lookups
        # =========================================================================
        
        indexes = [
            # Primary index for category browsing (no price filter)
            models.Index(
                fields=['is_active', 'category', '-created_at'],
                name='idx_product_category_sort'
            ),
            
            # Enhanced index for filtered searches (category + price)
            models.Index(
                fields=['is_active', 'category', 'price', '-created_at'],
                name='idx_product_full_search'
            ),
            
            # Secondary index for price-only searches
            models.Index(
                fields=['is_active', 'price'],
                name='idx_product_price_range'
            ),
            
            # Utility indexes for direct lookups
            models.Index(fields=['sku'], name='idx_product_sku'),
            models.Index(fields=['name'], name='idx_product_name'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"