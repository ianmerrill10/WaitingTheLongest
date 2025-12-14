"""
Waiting The Longest™ - Test Edge Cases
========================================
Tests for edge cases and boundary conditions.
"""

import pytest
from datetime import datetime, timedelta


class TestInputEdgeCases:
    """Test edge cases for input handling."""
    
    def test_empty_search_query(self, client):
        """Test searching with empty query."""
        response = client.get("/api/animals/search?q=")
        assert response.status_code == 200
        # Should return all animals or handle gracefully
    
    def test_search_special_characters(self, client):
        """Test search with special characters."""
        special_queries = [
            "dog & cat",
            "puppy (young)",
            "breed: labrador",
            "\"exact phrase\"",
            "test@email.com",
            "<script>alert('xss')</script>",
            "'; DROP TABLE animals; --",
        ]
        
        for query in special_queries:
            response = client.get(f"/api/animals/search?q={query}")
            # Should not crash, either 200 or 400
            assert response.status_code in [200, 400]
    
    def test_extremely_long_input(self, client):
        """Test handling of very long input strings."""
        long_string = "a" * 10000
        
        response = client.get(f"/api/animals/search?q={long_string}")
        # Should either truncate or return error, not crash
        assert response.status_code in [200, 400, 414]
    
    def test_unicode_input(self, client):
        """Test handling of unicode characters."""
        unicode_queries = [
            "Café dog",
            "猫 cat",
            "собака",
            "🐕 puppy",
            "naïve breed",
        ]
        
        for query in unicode_queries:
            response = client.get(f"/api/animals/search?q={query}")
            assert response.status_code == 200


class TestPaginationEdgeCases:
    """Test edge cases for pagination."""
    
    def test_page_zero(self, client):
        """Test requesting page 0."""
        response = client.get("/api/animals?page=0")
        # Should either treat as page 1 or return error
        assert response.status_code in [200, 400]
    
    def test_negative_page(self, client):
        """Test requesting negative page number."""
        response = client.get("/api/animals?page=-1")
        assert response.status_code in [200, 400]
    
    def test_very_large_page(self, client):
        """Test requesting a page number beyond available data."""
        response = client.get("/api/animals?page=999999")
        assert response.status_code == 200
        data = response.json()
        # Should return empty results
        assert len(data.get("items", [])) == 0
    
    def test_page_size_zero(self, client):
        """Test requesting page size of 0."""
        response = client.get("/api/animals?page_size=0")
        assert response.status_code in [200, 400]
    
    def test_page_size_very_large(self, client):
        """Test requesting very large page size."""
        response = client.get("/api/animals?page_size=10000")
        # Should cap at maximum allowed
        assert response.status_code == 200
    
    def test_non_numeric_pagination(self, client):
        """Test non-numeric pagination values."""
        response = client.get("/api/animals?page=abc&page_size=xyz")
        assert response.status_code in [200, 400, 422]


class TestDateEdgeCases:
    """Test edge cases for date handling."""
    
    def test_future_intake_date(self, test_db, animal_factory):
        """Test animal with future intake date."""
        future = datetime.utcnow() + timedelta(days=30)
        animal = animal_factory(intake_date=future)
        
        # Days waiting should be 0, not negative
        assert animal.days_waiting >= 0
    
    def test_very_old_intake_date(self, test_db, animal_factory):
        """Test animal with very old intake date."""
        old_date = datetime(2000, 1, 1)
        animal = animal_factory(intake_date=old_date)
        
        # Should handle gracefully
        assert animal.days_waiting > 8000
    
    def test_null_intake_date(self, test_db, animal_factory):
        """Test animal with null intake date."""
        animal = animal_factory(intake_date=None)
        
        # Should default to 0 or today
        assert animal.days_waiting is not None


class TestIdEdgeCases:
    """Test edge cases for ID handling."""
    
    def test_get_nonexistent_id(self, client):
        """Test getting an animal with non-existent ID."""
        response = client.get("/api/animals/999999")
        assert response.status_code == 404
    
    def test_get_negative_id(self, client):
        """Test getting an animal with negative ID."""
        response = client.get("/api/animals/-1")
        assert response.status_code in [400, 404]
    
    def test_get_non_numeric_id(self, client):
        """Test getting an animal with non-numeric ID."""
        response = client.get("/api/animals/abc")
        assert response.status_code in [400, 404, 422]
    
    def test_get_zero_id(self, client):
        """Test getting an animal with ID 0."""
        response = client.get("/api/animals/0")
        assert response.status_code in [400, 404]


class TestFilterEdgeCases:
    """Test edge cases for filtering."""
    
    def test_filter_invalid_species(self, client):
        """Test filtering with invalid species."""
        response = client.get("/api/animals?species=unicorn")
        assert response.status_code == 200
        # Should return empty results, not error
    
    def test_filter_invalid_state(self, client):
        """Test filtering with invalid state code."""
        response = client.get("/api/animals?state=XX")
        assert response.status_code in [200, 400]
    
    def test_multiple_filters_combined(self, client):
        """Test many filters at once."""
        response = client.get(
            "/api/animals?species=dog&breed=lab&age=young&gender=male&state=MA"
        )
        assert response.status_code == 200
    
    def test_conflicting_filters(self, client):
        """Test logically conflicting filters."""
        # No animal can be both dog and cat
        response = client.get("/api/animals?species=dog&species=cat")
        assert response.status_code == 200


class TestConcurrencyEdgeCases:
    """Test edge cases for concurrent operations."""
    
    def test_simultaneous_requests(self, client):
        """Test handling multiple simultaneous requests."""
        import concurrent.futures
        
        def make_request():
            return client.get("/api/animals")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in results)


class TestEmailEdgeCases:
    """Test edge cases for email handling."""
    
    def test_email_with_plus(self, client):
        """Test email with plus addressing."""
        response = client.post(
            "/api/newsletter/subscribe",
            json={"email": "test+tag@example.com"},
        )
        # Should be accepted
        assert response.status_code in [200, 201]
    
    def test_email_subdomain(self, client):
        """Test email with subdomain."""
        response = client.post(
            "/api/newsletter/subscribe",
            json={"email": "test@mail.example.com"},
        )
        assert response.status_code in [200, 201]
    
    def test_email_long_tld(self, client):
        """Test email with long TLD."""
        response = client.post(
            "/api/newsletter/subscribe",
            json={"email": "test@example.museum"},
        )
        assert response.status_code in [200, 201]
    
    def test_email_international(self, client):
        """Test international email domain."""
        response = client.post(
            "/api/newsletter/subscribe",
            json={"email": "test@例え.jp"},
        )
        # May or may not be supported
        assert response.status_code in [200, 201, 400, 422]


class TestEmptyStateEdgeCases:
    """Test edge cases when database is empty."""
    
    def test_get_animals_empty_db(self, client, empty_db):
        """Test getting animals when database is empty."""
        response = client.get("/api/animals")
        assert response.status_code == 200
        data = response.json()
        assert len(data.get("items", [])) == 0
    
    def test_stats_empty_db(self, client, empty_db):
        """Test getting stats when database is empty."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data.get("total_animals", 0) == 0
    
    def test_search_empty_db(self, client, empty_db):
        """Test searching when database is empty."""
        response = client.get("/api/animals/search?q=dog")
        assert response.status_code == 200
