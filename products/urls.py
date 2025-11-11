from django.urls import path
from . import views

urlpatterns = [
    path('api/products/search/', views.ProductSearchView.as_view(), name='product-search'),
    path('api/products/<int:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    
]