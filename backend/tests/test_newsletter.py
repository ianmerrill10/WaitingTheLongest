"""
===============================================================================
Waiting The Longest™ - Newsletter API Tests
===============================================================================
Tests for email newsletter subscription endpoints.
===============================================================================
"""

import pytest
from fastapi import status


class TestNewsletterSubscribeEndpoint:
    """Test /api/newsletter/subscribe endpoint"""
    
    def test_subscribe_success(self, client):
        """Test successful newsletter subscription"""
        response = client.post(
            "/api/newsletter/subscribe",
            json={
                "email": "test@example.com",
                "name": "Test User",
                "preferred_species": ["dog", "cat"],
                "location_state": "CA"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert "subscriber_id" in data
        assert "requires_verification" in data
    
    def test_subscribe_minimal(self, client):
        """Test subscription with only email"""
        response = client.post(
            "/api/newsletter/subscribe",
            json={
                "email": "minimal@example.com"
            }
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_subscribe_invalid_email(self, client):
        """Test subscription with invalid email"""
        response = client.post(
            "/api/newsletter/subscribe",
            json={
                "email": "not-an-email"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestNewsletterUnsubscribeEndpoint:
    """Test /api/newsletter/unsubscribe endpoint"""
    
    def test_unsubscribe_nonexistent(self, client):
        """Test unsubscribing non-existent email"""
        response = client.post(
            "/api/newsletter/unsubscribe?email=nonexistent@example.com"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return success=False for non-existent
        assert "success" in data


class TestEmailVerifyEndpoint:
    """Test /api/newsletter/verify endpoint"""
    
    def test_verify_invalid_token(self, client):
        """Test verification with invalid token"""
        response = client.get(
            "/api/newsletter/verify?email=test@example.com&token=invalid-token"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
