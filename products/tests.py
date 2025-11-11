from django.test import TestCase
from django.utils import timezone
from decimal import Decimal

from .models import Product, Category
from .services import ProductSearchService


class ProductModelTest(TestCase):
    """
    Test product model functionality and custom queryset methods
    """
    
    def setUp(self):
        """Create test data for product tests"""
        self.electronics = Category.objects.create(
            name="Electronics", 
            description="Phones, laptops, gadgets"
        )
        self.clothing = Category.objects.create(
            name="Clothing", 
            description="Shirts, pants, accessories"
        )
        
        # Create some active products
        self.phone = Product.objects.create(
            sku="PHONE001",
            name="Smartphone",
            price=Decimal('599.99'),
            is_active=True,
            category=self.electronics
        )
        
        self.laptop = Product.objects.create(
            sku="LAPTOP001", 
            name="Gaming Laptop",
            price=Decimal('1299.99'),
            is_active=True, 
            category=self.electronics
        )
        
        self.shirt = Product.objects.create(
            sku="SHIRT001",
            name="Cotton T-Shirt", 
            price=Decimal('24.99'),
            is_active=True,
            category=self.clothing
        )
        
        # Create an inactive product
        self.old_tablet = Product.objects.create(
            sku="TABLET001",
            name="Old Tablet",
            price=Decimal('199.99'),
            is_active=False,
            category=self.electronics
        )
    
    def test_product_creation(self):
        """Test that products are created correctly"""
        self.assertEqual(self.phone.name, "Smartphone")
        self.assertEqual(self.phone.sku, "PHONE001")
        self.assertEqual(self.phone.price, Decimal('599.99'))
        self.assertTrue(self.phone.is_active)
    
    def test_active_products_filter(self):
        """Test filtering to only active products"""
        active_products = Product.objects.active_products()
        self.assertEqual(active_products.count(), 3)
        
        # Verify inactive product is excluded
        self.assertFalse(active_products.filter(sku="TABLET001").exists())
    
    def test_category_filter(self):
        """Test filtering products by category"""
        electronics_products = Product.objects.by_category(self.electronics.id)
        self.assertEqual(electronics_products.count(), 3)  # Includes inactive
        
        electronics_active = Product.objects.active_products().by_category(self.electronics.id)
        self.assertEqual(electronics_active.count(), 2)  # Only active
    
    def test_price_range_filter(self):
        """Test filtering by price range"""
        # Mid-range products
        mid_priced = Product.objects.by_price_range(Decimal('500'), Decimal('700'))
        self.assertEqual(mid_priced.count(), 1)  # Just the phone
        
        # Budget products  
        budget_priced = Product.objects.by_price_range(Decimal('20'), Decimal('30'))
        self.assertEqual(budget_priced.count(), 1)  # Just the shirt
    
    def test_complex_search(self):
        """Test the main search method with multiple filters"""
        # Search for electronics between $500-$1500
        results = Product.objects.search_products(
            category_id=self.electronics.id,
            min_price=Decimal('500.00'),
            max_price=Decimal('1500.00')
        )
        
        self.assertEqual(results.count(), 2)  # Phone and laptop
        product_names = [p.name for p in results]
        self.assertIn("Smartphone", product_names)
        self.assertIn("Gaming Laptop", product_names)
        self.assertNotIn("Old Tablet", product_names)  # Inactive excluded
    
    def test_search_no_filters(self):
        """Test search with no filters returns all active products"""
        results = Product.objects.search_products()
        self.assertEqual(results.count(), 3)  # All active products
    
    def test_n1_query_optimization(self):
        """Test that we don't have N+1 query problem with categories"""
        with self.assertNumQueries(1):
            products = list(Product.objects.search_products(
                category_id=self.electronics.id
            ))
            # Access category data - should not trigger new queries
            for product in products:
                _ = product.category.name
                _ = product.category.description
    
    def test_default_ordering(self):
        """Test that products are ordered by newest first"""
        # Create a new product
        new_product = Product.objects.create(
            sku="NEW001",
            name="Newest Product", 
            price=Decimal('99.99'),
            is_active=True,
            category=self.electronics
        )
        
        products = Product.objects.active_products()
        self.assertEqual(products.first(), new_product)  # Newest should be first
    
    def test_index_definitions(self):
        """Test that all expected indexes are properly defined"""
        indexes = Product._meta.indexes
        index_names = [index.name for index in indexes]
        
        # Verify all expected indexes exist
        expected_indexes = [
            'idx_product_search_optimized',  # Your primary index
            'idx_product_price_range',       # Price range index
            'idx_product_sku',               # SKU index
            'idx_product_name',              # Name index
        ]
        
        for expected_index in expected_indexes:
            self.assertIn(expected_index, index_names, 
                         f"Index {expected_index} should be defined")
        
        # Verify the primary index has correct field structure
        search_index = next(
            idx for idx in indexes 
            if idx.name == 'idx_product_search_optimized'
        )
        self.assertEqual(
            search_index.fields, 
            ['is_active', 'category', '-created_at'],
            "Primary search index should have correct field order"
        )


class CategoryModelTest(TestCase):
    """Test category model functionality"""
    
    def test_category_creation(self):
        """Test basic category creation"""
        category = Category.objects.create(
            name="Home Goods",
            description="Furniture and decor"
        )
        self.assertEqual(category.name, "Home Goods")
        self.assertTrue(category.is_active)
    
    def test_category_string_representation(self):
        """Test the string representation"""
        category = Category.objects.create(name="Books")
        self.assertEqual(str(category), "Books")
    
    def test_category_indexes(self):
        """Test that category indexes are defined"""
        indexes = Category._meta.indexes
        index_names = [index.name for index in indexes]
        self.assertIn('idx_category_active_name', index_names)


class ProductSearchServiceTest(TestCase):
    """Test the service layer for product search"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            sku="TEST001",
            name="Test Product",
            price=Decimal('75.00'),
            is_active=True,
            category=self.category
        )
    
    def test_search_service_basic(self):
        """Test service layer with basic filters"""
        results = ProductSearchService.search_products({
            'category_id': self.category.id,
            'min_price': Decimal('50.00'),
            'max_price': Decimal('100.00')
        })
        
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().name, "Test Product")
    
    def test_get_product_detail(self):
        """Test retrieving single product with category data"""
        product = ProductSearchService.get_product_detail(self.product.id)
        self.assertEqual(product.name, "Test Product")
        self.assertEqual(product.category.name, "Test Category")


class ProductSearchViewTest(TestCase):
    """Test API view endpoints"""
    
    def setUp(self):
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            sku="VIEWTEST001",
            name="View Test Product", 
            price=Decimal('100.00'),
            is_active=True,
            category=self.category
        )
    
    def test_search_view_success(self):
        """Test successful search request"""
        response = self.client.get('/api/products/search/', {
            'category_id': str(self.category.id),
            'min_price': '50',
            'max_price': '150'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['products'][0]['name'], 'View Test Product')
    
    def test_search_view_invalid_price(self):
        """Test search with invalid price parameter"""
        response = self.client.get('/api/products/search/', {
            'min_price': 'not-a-number'
        })
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_product_detail_view(self):
        """Test single product retrieval"""
        response = self.client.get(f'/api/products/{self.product.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['product']['sku'], 'VIEWTEST001')
    
    def test_product_detail_not_found(self):
        """Test product detail with invalid ID"""
        response = self.client.get('/api/products/9999/')
        self.assertEqual(response.status_code, 404)