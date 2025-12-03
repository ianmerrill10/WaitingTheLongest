"""
===============================================================================
Waiting The Longest™ - Amazon Associates Tests
===============================================================================
Tests for affiliate link generation and product recommendations.
===============================================================================
"""

import pytest
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import with proper path setup
from monetization.amazon_associates import AmazonAssociates, AffiliateProduct


class TestAmazonAssociates:
    """Test Amazon Associates functionality"""
    
    def test_create_affiliate_link(self):
        """Test affiliate link generation"""
        link = AmazonAssociates.create_affiliate_link("B000OXAEIG")
        
        assert "amazon.com" in link
        assert "B000OXAEIG" in link
        assert "waitingthelon-20" in link
        assert "tag=" in link
    
    def test_create_affiliate_link_with_campaign(self):
        """Test affiliate link with custom campaign"""
        link = AmazonAssociates.create_affiliate_link("B000OXAEIG", campaign="homepage")
        
        assert "amazon.com" in link
        assert "waitingthelon-20" in link
    
    def test_get_recommendations_dog(self):
        """Test getting dog product recommendations"""
        recs = AmazonAssociates.get_recommendations(pet_type="dog", limit=5)
        
        assert len(recs) <= 5
        assert all("affiliate_url" in r for r in recs)
        assert all("amazon.com" in r["affiliate_url"] for r in recs)
    
    def test_get_recommendations_cat(self):
        """Test getting cat product recommendations"""
        recs = AmazonAssociates.get_recommendations(pet_type="cat", limit=5)
        
        assert len(recs) >= 1
        # Should include cat-specific products
        categories = [r["category"] for r in recs]
        assert any(cat in ["housing", "food", "furniture", "transport"] for cat in categories)
    
    def test_get_recommendations_puppy(self):
        """Test getting puppy-specific recommendations"""
        recs = AmazonAssociates.get_recommendations(pet_type="dog", pet_age="puppy", limit=10)
        
        assert len(recs) >= 1
        # Should prioritize puppy products
        names = [r["name"].lower() for r in recs]
        assert any("puppy" in name for name in names)
    
    def test_get_recommendations_by_category(self):
        """Test filtering by category"""
        recs = AmazonAssociates.get_recommendations(pet_type="dog", category="food", limit=5)
        
        assert all(r["category"] == "food" for r in recs)
    
    def test_get_new_pet_essentials_dog(self):
        """Test new pet essentials bundle for dogs"""
        result = AmazonAssociates.get_new_pet_essentials("dog")
        
        assert "title" in result
        assert "products" in result
        assert "disclosure" in result
        assert "dog" in result["title"].lower()
        assert "Amazon Associate" in result["disclosure"]
    
    def test_get_new_pet_essentials_cat(self):
        """Test new pet essentials bundle for cats"""
        result = AmazonAssociates.get_new_pet_essentials("cat")
        
        assert "cat" in result["title"].lower()
        assert len(result["products"]) >= 1
    
    def test_generate_html_widget(self):
        """Test HTML widget generation"""
        products = AmazonAssociates.get_recommendations(pet_type="dog", limit=3)
        html = AmazonAssociates.generate_html_widget(products, "Test Products")
        
        assert "Test Products" in html
        assert "wtl-affiliate-widget" in html
        assert "affiliate-disclosure" in html
        assert "amazon.com" in html


class TestAffiliateProduct:
    """Test AffiliateProduct model"""
    
    def test_create_product(self):
        """Test creating an affiliate product"""
        product = AffiliateProduct(
            product_id="test-product",
            name="Test Product",
            category="toys",
            pet_type="dog",
            amazon_asin="B123456789",
            price_range="$$"
        )
        
        assert product.product_id == "test-product"
        assert product.priority == 5  # Default priority
    
    def test_product_catalog_exists(self):
        """Test that product catalog has items"""
        catalog = AmazonAssociates.PRODUCT_CATALOG
        
        assert len(catalog) >= 10
        # Check required fields exist
        for product in catalog:
            assert product.product_id
            assert product.name
            assert product.amazon_asin
            assert product.category
            assert product.pet_type in ["dog", "cat", "both"]
