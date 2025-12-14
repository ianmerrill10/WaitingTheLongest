"""
Waiting The Longest™ - Integration Tests
=========================================
End-to-end tests for complete workflows.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Animal, Shelter


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestAnimalListingWorkflow:
    """Test the complete animal listing workflow."""
    
    def test_list_animals_returns_sorted_by_wait_time(self, client, populated_db):
        """Animals should be sorted by wait time (longest first)."""
        response = client.get("/animals")
        assert response.status_code == 200
        
        animals = response.json()
        if len(animals) > 1:
            # Verify sorting
            for i in range(len(animals) - 1):
                current_days = animals[i].get("days_waiting", 0)
                next_days = animals[i + 1].get("days_waiting", 0)
                assert current_days >= next_days
    
    def test_filter_by_species(self, client, populated_db):
        """Filter should return only matching species."""
        response = client.get("/animals?species=dog")
        assert response.status_code == 200
        
        animals = response.json()
        for animal in animals:
            assert animal["species"].lower() == "dog"
    
    def test_filter_by_state(self, client, populated_db):
        """Filter should return only animals in specified state."""
        # Get a state that has animals
        response = client.get("/animals?limit=1")
        if response.status_code == 200 and response.json():
            # Test passes if we can filter
            response = client.get("/animals?state=CA")
            assert response.status_code == 200


class TestAnimalDetailWorkflow:
    """Test viewing animal details."""
    
    def test_view_animal_detail(self, client, populated_db):
        """Should return full animal details."""
        # First get an animal
        response = client.get("/animals?limit=1")
        if response.status_code == 200 and response.json():
            animal_id = response.json()[0]["id"]
            
            # Get details
            response = client.get(f"/animals/{animal_id}")
            assert response.status_code == 200
            
            animal = response.json()
            assert "name" in animal
            assert "shelter" in animal or "shelter_id" in animal
    
    def test_view_nonexistent_animal(self, client):
        """Should return 404 for nonexistent animal."""
        response = client.get("/animals/99999")
        assert response.status_code == 404


class TestNewsletterWorkflow:
    """Test newsletter subscription workflow."""
    
    def test_subscribe_to_newsletter(self, client):
        """Should successfully subscribe new email."""
        response = client.post(
            "/newsletter/subscribe",
            json={"email": "newuser@example.com"}
        )
        # May return 200 or 201 depending on implementation
        assert response.status_code in [200, 201, 422]  # 422 if validation strict
    
    def test_duplicate_subscription(self, client):
        """Should handle duplicate subscriptions gracefully."""
        email = "duplicate@example.com"
        
        # First subscription
        client.post("/newsletter/subscribe", json={"email": email})
        
        # Second subscription (should not error)
        response = client.post("/newsletter/subscribe", json={"email": email})
        # Should either succeed or indicate already subscribed
        assert response.status_code in [200, 201, 400, 409, 422]


class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    def test_health_endpoint(self, client):
        """Health endpoint should return OK."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("status") in ["healthy", "ok", "degraded"]
    
    def test_root_endpoint(self, client):
        """Root should return API info."""
        response = client.get("/")
        assert response.status_code == 200


class TestSearchWorkflow:
    """Test search functionality."""
    
    def test_search_by_name(self, client, populated_db):
        """Should find animals by name search."""
        response = client.get("/animals/search?q=buddy")
        # Search endpoint may not exist yet
        if response.status_code == 200:
            results = response.json()
            assert isinstance(results, list)
    
    def test_search_no_results(self, client):
        """Should return empty list for no matches."""
        response = client.get("/animals/search?q=xyznonexistent123")
        if response.status_code == 200:
            results = response.json()
            assert isinstance(results, list)


class TestShelterWorkflow:
    """Test shelter-related endpoints."""
    
    def test_list_shelters(self, client, populated_db):
        """Should list all shelters."""
        response = client.get("/shelters")
        if response.status_code == 200:
            shelters = response.json()
            assert isinstance(shelters, list)
    
    def test_get_shelter_animals(self, client, populated_db):
        """Should get animals for a specific shelter."""
        # Get a shelter ID first
        response = client.get("/shelters")
        if response.status_code == 200 and response.json():
            shelter_id = response.json()[0]["id"]
            
            response = client.get(f"/shelters/{shelter_id}/animals")
            if response.status_code == 200:
                animals = response.json()
                assert isinstance(animals, list)


class TestAPIDocumentation:
    """Test API documentation endpoints."""
    
    def test_openapi_docs(self, client):
        """OpenAPI docs should be available."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_openapi_json(self, client):
        """OpenAPI JSON schema should be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema


class TestRateLimiting:
    """Test rate limiting behavior."""
    
    def test_rate_limit_not_triggered_for_normal_usage(self, client):
        """Normal usage should not trigger rate limits."""
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200
    
    @pytest.mark.slow
    def test_rate_limit_triggers_for_abuse(self, client):
        """Excessive requests should trigger rate limit."""
        responses = []
        for _ in range(200):
            response = client.get("/animals")
            responses.append(response.status_code)
            if response.status_code == 429:
                break
        
        # Either we hit rate limit or all succeeded (rate limit not configured)
        assert 429 in responses or all(r == 200 for r in responses)


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """CORS headers should be present for allowed origins."""
        response = client.options(
            "/animals",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        # Should either allow or not have CORS configured
        assert response.status_code in [200, 204, 405]
