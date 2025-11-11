from django.http import JsonResponse
from django.views import View
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
import decimal

from .services import ProductSearchService
from .models import Product


class ProductSearchView(View):
    """
    API endpoint for searching and filtering products
    Handles category filtering, price ranges, and basic validation
    """
    
    def get(self, request):
        """
        Handle GET requests for product search
        Supports category_id, min_price, and max_price parameters
        """
        try:
            # Extract and validate parameters
            category_id = self._get_category_id(request)
            min_price, max_price = self._get_price_range(request)
            
            # Validate price range makes sense
            if min_price is not None and max_price is not None:
                if min_price > max_price:
                    return JsonResponse({
                        'success': False,
                        'error': 'Minimum price cannot be greater than maximum price'
                    }, status=400)
            
            # Build filters dictionary
            filters = {
                'category_id': category_id,
                'min_price': min_price,
                'max_price': max_price,
            }
            
            # Execute search using service layer
            products_queryset = ProductSearchService.search_products(filters)
            
            # Convert to JSON-serializable format
            products_data = []
            for product in products_queryset:
                products_data.append({
                    'id': product.id,
                    'sku': product.sku,
                    'name': product.name,
                    'price': str(product.price),  # Convert Decimal to string for JSON
                    'is_active': product.is_active,
                    'category': {
                        'id': product.category.id,
                        'name': product.category.name
                    },
                    'created_at': product.created_at.isoformat(),
                    'description': product.description,
                })
            
            # Return successful response
            return JsonResponse({
                'success': True,
                'products': products_data,
                'count': len(products_data),
                'filters_applied': filters
            })
            
        except ValueError as e:
            # Handle validation errors
            return JsonResponse({
                'success': False,
                'error': f'Invalid parameter: {str(e)}'
            }, status=400)
        except DatabaseError as e:
            # Handle database errors
            return JsonResponse({
                'success': False,
                'error': 'Database error occurred'
            }, status=500)
        except Exception as e:
            # Handle unexpected errors
            return JsonResponse({
                'success': False,
                'error': f'Unexpected server error: {str(e)}'
            }, status=500)
    
    def _get_category_id(self, request):
        """Extract and validate category_id from request parameters"""
        category_id = request.GET.get('category_id')
        if category_id:
            try:
                return int(category_id)
            except (ValueError, TypeError):
                raise ValueError('category_id must be a valid number')
        return None
    
    def _get_price_range(self, request):
        """Extract and validate price range parameters"""
        min_price_str = request.GET.get('min_price')
        max_price_str = request.GET.get('max_price')
        
        min_price = None
        max_price = None
        
        # Parse min_price if provided
        if min_price_str:
            try:
                min_price = decimal.Decimal(min_price_str)
                if min_price < 0:
                    raise ValueError('Price cannot be negative')
            except (ValueError, decimal.InvalidOperation):
                raise ValueError('min_price must be a valid dollar amount')
        
        # Parse max_price if provided  
        if max_price_str:
            try:
                max_price = decimal.Decimal(max_price_str)
                if max_price < 0:
                    raise ValueError('Price cannot be negative')
            except (ValueError, decimal.InvalidOperation):
                raise ValueError('max_price must be a valid dollar amount')
        
        return min_price, max_price


class ProductDetailView(View):
    """
    API endpoint for retrieving single product details
    """
    
    def get(self, request, product_id):
        """
        Handle GET requests for single product
        """
        try:
            # Basic product_id validation
            if not isinstance(product_id, int) and not product_id.isdigit():
                return JsonResponse({
                    'success': False,
                    'error': 'Product ID must be a valid number'
                }, status=400)
            
            product_id = int(product_id)
            
            # Get product with optimized query
            product = ProductSearchService.get_product_detail(product_id)
            
            # Build response data
            product_data = {
                'id': product.id,
                'sku': product.sku,
                'name': product.name,
                'price': str(product.price),
                'is_active': product.is_active,
                'category': {
                    'id': product.category.id,
                    'name': product.category.name
                },
                'description': product.description,
                'created_at': product.created_at.isoformat(),
            }
            
            return JsonResponse({
                'success': True,
                'product': product_data
            })
            
        except ObjectDoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Product not found'
            }, status=404)
        except DatabaseError:
            return JsonResponse({
                'success': False,
                'error': 'Database error occurred'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }, status=500)