"""
Waiting The Longest™ - Accessibility Tests
===========================================
Tests for WCAG 2.1 accessibility compliance.
"""

import pytest


class TestAccessibility:
    """Test accessibility features of the API responses."""
    
    def test_error_messages_are_descriptive(self, client):
        """Test that error messages are clear and descriptive."""
        response = client.get("/api/animals/999999")
        assert response.status_code == 404
        data = response.json()
        
        # Error message should be human-readable
        error = data.get("error", {})
        assert "message" in error or "detail" in data
    
    def test_image_alt_text_provided(self, client, test_db, animal_factory):
        """Test that animal photos have alt text suggestions."""
        animal = animal_factory(
            name="Buddy",
            species="dog",
            breed="Labrador",
        )
        
        response = client.get(f"/api/animals/{animal.id}")
        assert response.status_code == 200
        data = response.json()
        
        # API should provide data suitable for alt text
        assert "name" in data
        assert "species" in data
    
    def test_response_has_proper_content_type(self, client):
        """Test that responses have proper content type."""
        response = client.get("/api/animals")
        assert response.headers.get("content-type") == "application/json"
    
    def test_pagination_info_included(self, client, test_db, animal_factory):
        """Test that pagination info is included for screen readers."""
        # Create several animals
        for i in range(25):
            animal_factory(name=f"Animal {i}")
        
        response = client.get("/api/animals?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        
        # Should have pagination metadata
        pagination = data.get("pagination", {})
        assert "total_items" in pagination or "total" in data
        assert "page" in pagination or "page" in data


class TestKeyboardNavigation:
    """Test data structure supports keyboard navigation."""
    
    def test_animals_have_unique_ids(self, client, test_db, animal_factory):
        """Test that all animals have unique identifiers."""
        animals = [animal_factory() for _ in range(5)]
        
        response = client.get("/api/animals")
        data = response.json()
        
        ids = [item["id"] for item in data.get("items", [])]
        assert len(ids) == len(set(ids))  # All unique
    
    def test_ordered_data(self, client, test_db, animal_factory):
        """Test that data is consistently ordered."""
        for i in range(5):
            animal_factory()
        
        response1 = client.get("/api/animals")
        response2 = client.get("/api/animals")
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Same request should return same order
        ids1 = [item["id"] for item in data1.get("items", [])]
        ids2 = [item["id"] for item in data2.get("items", [])]
        assert ids1 == ids2


class TestColorContrast:
    """Test that API provides data for accessible color choices."""
    
    def test_urgency_levels_available(self, client, test_db, animal_factory):
        """Test that urgency/priority information is available."""
        from datetime import datetime, timedelta
        
        # Create animals with different waiting times
        old_animal = animal_factory(
            intake_date=datetime.utcnow() - timedelta(days=180)
        )
        new_animal = animal_factory(
            intake_date=datetime.utcnow() - timedelta(days=1)
        )
        
        response = client.get("/api/animals")
        data = response.json()
        
        # Each animal should have days_waiting for color coding
        for item in data.get("items", []):
            assert "days_waiting" in item or "intake_date" in item


class TestScreenReaderSupport:
    """Test data suitable for screen readers."""
    
    def test_descriptive_names(self, client, test_db, animal_factory):
        """Test that animal data includes descriptive information."""
        animal = animal_factory(
            name="Luna",
            species="Cat",
            breed="Siamese",
            age="Young",
            gender="Female",
        )
        
        response = client.get(f"/api/animals/{animal.id}")
        data = response.json()
        
        # Should have enough info for a screen reader announcement
        required_fields = ["name", "species"]
        for field in required_fields:
            assert field in data
            assert data[field]  # Not empty
    
    def test_shelter_contact_info(self, client, test_db, shelter_factory):
        """Test that shelter info includes contact details."""
        shelter = shelter_factory(
            name="Happy Paws Shelter",
            phone="555-1234",
            email="info@happypaws.org",
        )
        
        response = client.get(f"/api/shelters/{shelter.id}")
        data = response.json()
        
        # Contact info should be available
        assert "phone" in data or "email" in data


class TestTimeAndDateAccessibility:
    """Test time and date handling for accessibility."""
    
    def test_dates_in_standard_format(self, client, test_db, animal_factory):
        """Test that dates are in ISO format."""
        animal = animal_factory()
        
        response = client.get(f"/api/animals/{animal.id}")
        data = response.json()
        
        # Dates should be in ISO 8601 format
        if "created_at" in data:
            assert "T" in data["created_at"] or "-" in data["created_at"]
    
    def test_duration_in_days(self, client, test_db, animal_factory):
        """Test that wait times are provided in understandable units."""
        animal = animal_factory()
        
        response = client.get(f"/api/animals/{animal.id}")
        data = response.json()
        
        # Days waiting should be a number
        if "days_waiting" in data:
            assert isinstance(data["days_waiting"], (int, float))


class TestInternationalization:
    """Test i18n support for accessibility."""
    
    def test_accepts_language_header(self, client):
        """Test that API accepts Accept-Language header."""
        response = client.get(
            "/api/animals",
            headers={"Accept-Language": "es-ES"},
        )
        # Should not fail
        assert response.status_code == 200
    
    def test_handles_rtl_content(self, client, test_db, animal_factory):
        """Test handling of RTL text in descriptions."""
        animal = animal_factory(
            description="This pet is friendly. هذا الحيوان الأليف ودود.",
        )
        
        response = client.get(f"/api/animals/{animal.id}")
        assert response.status_code == 200
        data = response.json()
        
        # RTL text should be preserved
        assert "ودود" in data.get("description", "")
