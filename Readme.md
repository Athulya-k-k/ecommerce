# E-commerce Product Search API

A fast Django API for searching and filtering products with optimized database performance.

## Features

- Search products by category and price range
- Optimized database indexing for speed
- Prevents N+1 query problems
- Clean REST API with error handling

## Quick Start


# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate

# Run server
python manage.py runserver


# API Usage

# Search Products

bash
# All active products
GET /api/products/search/

# Filter by category
GET /api/products/search/?category_id=1

# Filter by price
GET /api/products/search/?min_price=10&max_price=100

# Combined filters
GET /api/products/search/?category_id=1&min_price=50&max_price=500

# Get Product Details

GET /api/products/1/