"""
===============================================================================
Waiting The Longest™ - Product Recommendations API Tests
===============================================================================
Tests for affiliate product recommendation endpoints.
===============================================================================
"""

import pytest
from fastapi import status


class TestProductRecommendationsEndpoint:
    """Test /api/products/recommendations endpoint"""
    
    def test_get_dog_recommendations(self, client):
        """Test getting product recommendations for dogs"""
        response = client.get("/api/products/recommendations?pet_type=dog")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data
        assert "count" in data
        assert data["pet_type"] == "dog"
        assert "disclosure" in data
    
    def test_get_cat_recommendations(self, client):
        """Test getting product recommendations for cats"""
        response = client.get("/api/products/recommendations?pet_type=cat")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pet_type"] == "cat"
    
    def test_get_recommendations_with_age(self, client):
        """Test getting recommendations with age filter"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_age=puppy")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["pet_type"] == "dog"
    
    def test_get_recommendations_with_size(self, client):
        """Test getting recommendations with size filter"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_size=large")
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_recommendations_with_limit(self, client):
        """Test limiting number of recommendations"""
        response = client.get("/api/products/recommendations?pet_type=dog&limit=3")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] <= 3
    
    def test_invalid_pet_type(self, client):
        """Test invalid pet_type returns error"""
        response = client.get("/api/products/recommendations?pet_type=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_invalid_pet_age(self, client):
        """Test invalid pet_age returns error"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_age=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_invalid_pet_size(self, client):
        """Test invalid pet_size returns error"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_size=invalid")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAffiliateClickEndpoint:
    """Test /api/affiliate/click endpoint"""
    
    def test_track_affiliate_click(self, client):
        """Test tracking an affiliate click"""
        response = client.post("/api/affiliate/click?product_id=test-product-123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert "click_id" in data
    
    def test_track_affiliate_click_with_source(self, client):
        """Test tracking click with source page"""
        response = client.post(
            "/api/affiliate/click?product_id=test-product-123&source_page=animal-detail"
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_track_affiliate_click_with_animal_id(self, client, sample_animal):
        """Test tracking click with associated animal"""
        response = client.post(
            f"/api/affiliate/click?product_id=test-product-123&animal_id={sample_animal.id}"
        )
        assert response.status_code == status.HTTP_200_OK
