"""
===============================================================================
Waiting The Longest™ - Shelters API Tests
===============================================================================
Tests for the new shelters, breeds, and filters endpoints.
===============================================================================
"""

import pytest
from fastapi import status


class TestSheltersEndpoint:
    """Test /api/shelters endpoint"""
    
    def test_list_shelters_empty(self, client):
        """Test listing shelters when database is empty"""
        response = client.get("/api/shelters")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
    
    def test_list_shelters_with_data(self, client, sample_shelter):
        """Test listing shelters with data"""
        response = client.get("/api/shelters")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
        assert data["items"][0]["name"] == sample_shelter.name
    
    def test_filter_shelters_by_state(self, client, sample_shelter):
        """Test filtering shelters by state"""
        response = client.get(f"/api/shelters?state={sample_shelter.state}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for item in data["items"]:
            assert sample_shelter.state.lower() in item["state"].lower()
    
    def test_get_shelter_detail(self, client, sample_shelter):
        """Test getting shelter detail"""
        response = client.get(f"/api/shelters/{sample_shelter.id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == sample_shelter.id
        assert data["name"] == sample_shelter.name
        assert data["city"] == sample_shelter.city
    
    def test_get_shelter_not_found(self, client):
        """Test getting non-existent shelter"""
        response = client.get("/api/shelters/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestBreedsEndpoint:
    """Test /api/breeds endpoint"""
    
    def test_list_breeds_empty(self, client):
        """Test listing breeds when database is empty"""
        response = client.get("/api/breeds")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["breeds"] == []
        assert data["count"] == 0
    
    def test_list_breeds_with_data(self, client, multiple_animals):
        """Test listing breeds with data"""
        response = client.get("/api/breeds")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] > 0
        assert len(data["breeds"]) > 0
    
    def test_filter_breeds_by_species(self, client, multiple_animals):
        """Test filtering breeds by species"""
        response = client.get("/api/breeds?species=dog")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["species"] == "dog"
        # Should include dog breeds but not cat breeds


class TestFiltersEndpoint:
    """Test /api/filters endpoint"""
    
    def test_get_filter_options_empty(self, client):
        """Test getting filter options when database is empty"""
        response = client.get("/api/filters")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "species" in data
        assert "age_groups" in data
        assert "sizes" in data
        assert "genders" in data
        assert "states" in data
    
    def test_get_filter_options_with_data(self, client, multiple_animals):
        """Test getting filter options with data"""
        response = client.get("/api/filters")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Should have species counts
        species = [s["value"] for s in data["species"]]
        assert "dog" in species or "cat" in species
        
        # Each filter option should have value and count
        for item in data["species"]:
            assert "value" in item
            assert "count" in item
            assert item["count"] > 0


class TestSimilarAnimalsEndpoint:
    """Test /api/animals/{id}/similar endpoint"""
    
    def test_get_similar_animals(self, client, multiple_animals):
        """Test getting similar animals"""
        # Get first animal ID
        response = client.get("/api/animals")
        assert response.status_code == status.HTTP_200_OK
        animals = response.json()["items"]
        if not animals:
            pytest.skip("No animals in database")
        
        animal_id = animals[0]["id"]
        response = client.get(f"/api/animals/{animal_id}/similar")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "similar_to" in data
        assert "items" in data
        assert "count" in data
    
    def test_similar_animals_not_found(self, client):
        """Test getting similar animals for non-existent animal"""
        response = client.get("/api/animals/99999/similar")
        assert response.status_code == status.HTTP_404_NOT_FOUND
