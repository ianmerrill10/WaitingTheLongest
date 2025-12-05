"""
===============================================================================
Waiting The Longest™ - API Endpoint Tests
===============================================================================
Comprehensive tests for all FastAPI endpoints.

Endpoints tested:
- / (root)
- /health
- /api/animals (list with filters)
- /api/animals/{id} (detail)
- /api/longest-waiting
- /api/success-stories (GET and POST)
- /api/stats
- /api/affiliate/click
- /api/products/recommendations

===============================================================================
"""

import pytest
from fastapi import status
from unittest.mock import patch, MagicMock

from app.data.rescue_directory import RESCUE_DIRECTORY


class TestRootEndpoints:
    """Test root and health endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/api")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Waiting The Longest™ API"
        assert data["tagline"] == "Because Every Day Matters"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"
        assert data["documentation"] == "/api/docs"
    
    def test_health_check_healthy(self, client):
        """Test health check endpoint returns healthy status"""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"
    
    def test_health_check_response_format(self, client):
        """Test health check response format matches schema"""
        response = client.get("/health")
        data = response.json()
        
        # All required fields should be present
        required_fields = ["status", "database", "timestamp", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_lightweight_healthz(self, client):
        """Lightweight probe should respond quickly with ok status"""
        response = client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_readyz_endpoint(self, client):
        """Readiness probe reports dependency checks and uptime"""
        response = client.get("/readyz")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "uptime_seconds" in data and data["uptime_seconds"] >= 0
        assert "rescue_directory_version" in data
        assert "checks" in data and "database" in data["checks"]


class TestAnimalListEndpoint:
    """Test animal listing endpoint /api/animals"""
    
    def test_list_animals_empty(self, client):
        """Test listing animals when database is empty"""
        response = client.get("/api/animals")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total_pages"] == 0
        assert data["has_next"] == False
        assert data["has_prev"] == False
    
    def test_list_animals_with_data(self, client, multiple_animals):
        """Test listing animals with data"""
        response = client.get("/api/animals")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only return available animals (3 out of 4)
        assert data["total"] == 3
        assert len(data["items"]) == 3
    
    def test_list_animals_sorted_by_days_waiting(self, client, multiple_animals):
        """Test that animals are sorted by days_waiting descending by default"""
        response = client.get("/api/animals?sort_by=days_waiting&sort_order=desc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # First animal should be Buddy (500 days)
        assert data["items"][0]["canonical_name"] == "Buddy"
        assert data["items"][0]["days_waiting"] >= 499  # Allow for slight timing differences
        
        # Last should be Luna (50 days)
        assert data["items"][-1]["canonical_name"] == "Luna"
    
    def test_list_animals_sorted_ascending(self, client, multiple_animals):
        """Test sorting animals in ascending order (newest first)"""
        response = client.get("/api/animals?sort_by=days_waiting&sort_order=asc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # First animal should be Luna (50 days - shortest wait)
        assert data["items"][0]["canonical_name"] == "Luna"
    
    def test_filter_by_species_dog(self, client, multiple_animals):
        """Test filtering animals by species - dogs"""
        response = client.get("/api/animals?species=dog")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2  # Buddy and Luna (not Rocky who is adopted)
        for item in data["items"]:
            assert item["species"] == "dog"
    
    def test_filter_by_species_cat(self, client, multiple_animals):
        """Test filtering animals by species - cats"""
        response = client.get("/api/animals?species=cat")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["species"] == "cat"
        assert data["items"][0]["canonical_name"] == "Whiskers"
    
    def test_filter_by_status_available(self, client, multiple_animals):
        """Test filtering animals by available status (default)"""
        response = client.get("/api/animals?status=available")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        for item in data["items"]:
            assert item["status"] == "available"
    
    def test_filter_by_status_adopted(self, client, multiple_animals):
        """Test filtering animals by adopted status"""
        response = client.get("/api/animals?status=adopted")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["canonical_name"] == "Rocky"
        assert data["items"][0]["status"] == "adopted"
    
    def test_filter_by_breed(self, client, multiple_animals):
        """Test filtering animals by breed (partial match)"""
        response = client.get("/api/animals?breed=Shepherd")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["canonical_name"] == "Buddy"
    
    def test_filter_by_age_group(self, client, multiple_animals):
        """Test filtering animals by age group"""
        response = client.get("/api/animals?age_group=puppy")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["canonical_name"] == "Luna"
        assert data["items"][0]["age_group"] == "puppy"
    
    def test_filter_by_size(self, client, multiple_animals):
        """Test filtering animals by size"""
        response = client.get("/api/animals?size=large")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["canonical_name"] == "Buddy"
    
    def test_filter_by_gender(self, client, multiple_animals):
        """Test filtering animals by gender"""
        response = client.get("/api/animals?gender=female")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 2  # Whiskers and Luna
        for item in data["items"]:
            assert item["gender"] == "female"
    
    def test_filter_combined(self, client, multiple_animals):
        """Test combining multiple filters"""
        response = client.get("/api/animals?species=dog&gender=female&status=available")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["canonical_name"] == "Luna"
    
    def test_pagination_first_page(self, client, multiple_animals):
        """Test pagination - first page"""
        response = client.get("/api/animals?page=1&page_size=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["has_next"] == True
        assert data["has_prev"] == False
        assert data["total_pages"] == 2
    
    def test_pagination_second_page(self, client, multiple_animals):
        """Test pagination - second page"""
        response = client.get("/api/animals?page=2&page_size=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["page"] == 2
        assert data["has_next"] == False
        assert data["has_prev"] == True
    
    def test_pagination_invalid_page(self, client, multiple_animals):
        """Test pagination with page beyond available data"""
        response = client.get("/api/animals?page=100&page_size=20")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["items"] == []
    
    def test_pagination_page_size_limit(self, client, multiple_animals):
        """Test that page_size is limited to 100"""
        response = client.get("/api/animals?page_size=200")
        # Should return 422 because page_size > 100
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_response_item_structure(self, client, sample_animal):
        """Test that response items have correct structure"""
        response = client.get("/api/animals")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        item = data["items"][0]
        required_fields = [
            "id", "species", "canonical_name", "breed_primary", 
            "age_group", "size", "gender", "status", "days_waiting", "first_seen_at"
        ]
        for field in required_fields:
            assert field in item, f"Missing required field: {field}"


class TestAnimalDetailEndpoint:
    """Test animal detail endpoint /api/animals/{id}"""
    
    def test_get_animal_detail(self, client, sample_animal_with_observation):
        """Test getting animal detail by ID"""
        animal_id = sample_animal_with_observation.id
        response = client.get(f"/api/animals/{animal_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == animal_id
        assert data["canonical_name"] == "Max"
        assert data["breed_primary"] == "Labrador Retriever"
        assert data["days_waiting"] >= 99
        assert len(data["observations"]) == 1
    
    def test_get_animal_detail_includes_photos(self, client, sample_animal_with_observation):
        """Test that animal detail includes photos from observations"""
        animal_id = sample_animal_with_observation.id
        response = client.get(f"/api/animals/{animal_id}")
        data = response.json()
        
        assert "photos" in data
        assert len(data["photos"]) > 0
        assert "https://example.com/max.jpg" in data["photos"]
    
    def test_get_animal_detail_includes_description(self, client, sample_animal_with_observation):
        """Test that animal detail includes description"""
        animal_id = sample_animal_with_observation.id
        response = client.get(f"/api/animals/{animal_id}")
        data = response.json()
        
        assert data["description"] == "Friendly and playful dog looking for a forever home!"
    
    def test_get_animal_detail_includes_shelter_info(self, client, sample_animal_with_observation):
        """Test that animal detail includes shelter information"""
        animal_id = sample_animal_with_observation.id
        response = client.get(f"/api/animals/{animal_id}")
        data = response.json()
        
        assert "shelter_info" in data
        assert data["shelter_info"]["name"] == "Test Animal Shelter"
        assert data["shelter_info"]["state"] == "TX"
    
    def test_get_animal_not_found(self, client):
        """Test getting non-existent animal returns 404"""
        response = client.get("/api/animals/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Animal not found"
    
    def test_get_animal_invalid_id(self, client):
        """Test getting animal with invalid ID format"""
        response = client.get("/api/animals/invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLongestWaitingEndpoint:
    """Test the longest-waiting animals endpoint /api/longest-waiting"""
    
    def test_longest_waiting(self, client, multiple_animals):
        """Test longest waiting endpoint returns correct order"""
        response = client.get("/api/longest-waiting?limit=3")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "animals" in data
        assert "message" in data
        assert "mission" in data
        assert data["mission"] == "Because Every Day Matters"
        
        # Buddy should be first (500 days)
        assert data["animals"][0]["canonical_name"] == "Buddy"
    
    def test_longest_waiting_default_limit(self, client, multiple_animals):
        """Test longest waiting with default limit of 10"""
        response = client.get("/api/longest-waiting")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["animals"]) == 3  # Only 3 available animals
    
    def test_longest_waiting_filter_species(self, client, multiple_animals):
        """Test longest waiting with species filter"""
        response = client.get("/api/longest-waiting?species=cat&limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["animals"]) == 1
        assert data["animals"][0]["canonical_name"] == "Whiskers"
    
    def test_longest_waiting_only_available(self, client, multiple_animals):
        """Test that only available animals are returned"""
        response = client.get("/api/longest-waiting?limit=10")
        data = response.json()
        
        # Rocky is adopted and should not appear
        names = [a["canonical_name"] for a in data["animals"]]
        assert "Rocky" not in names
    
    def test_longest_waiting_limit_validation(self, client):
        """Test limit parameter validation"""
        response = client.get("/api/longest-waiting?limit=100")
        # Should fail validation - limit max is 50
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSuccessStoriesEndpoints:
    """Test success stories endpoints /api/success-stories"""
    
    def test_get_success_stories_empty(self, client):
        """Test getting success stories when none exist"""
        response = client.get("/api/success-stories")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["stories"] == []
        assert data["message"] == "Every adoption is a victory!"
    
    def test_get_success_stories(self, client, sample_success_story):
        """Test getting success stories"""
        response = client.get("/api/success-stories")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["stories"]) == 1
        assert data["stories"][0]["pet_name"] == "Max"
        assert data["stories"][0]["days_waited"] == 100
    
    def test_get_success_stories_only_approved(self, client, unapproved_success_story):
        """Test that only approved stories are returned"""
        response = client.get("/api/success-stories")
        data = response.json()
        # Unapproved story should not appear
        assert len(data["stories"]) == 0
    
    def test_get_success_stories_with_limit(self, client, sample_success_story):
        """Test success stories with custom limit"""
        response = client.get("/api/success-stories?limit=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["stories"]) <= 5
    
    def test_submit_success_story(self, client, sample_animal):
        """Test submitting a success story"""
        story_data = {
            "pet_name": "Max",
            "adopter_name": "Jane Doe",
            "story_text": "This is a wonderful story about how Max found his forever home after waiting so long. We are so happy to have him in our family!",
            "days_waited": 100,
            "animal_id": sample_animal.id,
            "contact_email": "jane@example.com"
        }
        response = client.post("/api/success-stories", json=story_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert "story_id" in data
        assert "Thank you for sharing" in data["message"]
    
    def test_submit_success_story_minimal(self, client):
        """Test submitting a success story with minimal required fields"""
        story_data = {
            "pet_name": "NewPet",
            "story_text": "This is a test story that is long enough to meet the minimum character requirement for validation purposes.",
            "days_waited": 50
        }
        response = client.post("/api/success-stories", json=story_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
    
    def test_submit_success_story_validation_short_text(self, client):
        """Test success story validation - story text too short"""
        story_data = {
            "pet_name": "Max",
            "story_text": "Too short",
            "days_waited": 100
        }
        response = client.post("/api/success-stories", json=story_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_submit_success_story_validation_missing_name(self, client):
        """Test success story validation - missing pet name"""
        story_data = {
            "story_text": "This is a test story that is long enough to meet the minimum character requirement.",
            "days_waited": 100
        }
        response = client.post("/api/success-stories", json=story_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_submit_success_story_invalid_email(self, client):
        """Test success story validation - invalid email format"""
        story_data = {
            "pet_name": "Max",
            "story_text": "This is a test story that is long enough to meet the minimum character requirement for validation.",
            "days_waited": 100,
            "contact_email": "not-an-email"
        }
        response = client.post("/api/success-stories", json=story_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestStatsEndpoint:
    """Test statistics endpoint /api/stats"""
    
    def test_stats_empty(self, client):
        """Test stats with empty database"""
        response = client.get("/api/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_animals"] == 0
        assert data["available_animals"] == 0
        assert data["mission"] == "Because Every Day Matters"
        assert "updated_at" in data
    
    def test_stats_with_animals(self, client, multiple_animals):
        """Test stats with animals data"""
        response = client.get("/api/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_animals"] == 4  # All animals including adopted
        assert data["available_animals"] == 3  # Only available
        assert data["longest_wait_days"] >= 499
    
    def test_stats_with_success_stories(self, client, sample_success_story):
        """Test stats include success story count"""
        response = client.get("/api/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success_stories"] == 1
    
    def test_stats_response_structure(self, client):
        """Test stats response has all required fields"""
        response = client.get("/api/stats")
        data = response.json()
        
        required_fields = [
            "total_animals", "available_animals", "average_wait_days",
            "longest_wait_days", "success_stories", "mission", "updated_at"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestAffiliateEndpoints:
    """Test affiliate/monetization endpoints"""
    
    def test_track_affiliate_click(self, client, sample_animal):
        """Test tracking affiliate click"""
        response = client.post(
            "/api/affiliate/click",
            params={
                "product_id": "dog-food-test",
                "source_page": "animal_detail",
                "animal_id": sample_animal.id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
        assert "click_id" in data
    
    def test_track_affiliate_click_minimal(self, client):
        """Test tracking affiliate click with minimal data"""
        response = client.post(
            "/api/affiliate/click",
            params={"product_id": "test-product"}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] == True
    
    def test_track_affiliate_click_missing_product_id(self, client):
        """Test affiliate click requires product_id"""
        response = client.post("/api/affiliate/click")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_get_product_recommendations_dog(self, client):
        """Test getting product recommendations for dogs"""
        response = client.get("/api/products/recommendations?pet_type=dog")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "products" in data
        assert "disclosure" in data
        assert "Amazon Associate" in data["disclosure"]
        assert len(data["products"]) > 0
    
    def test_get_product_recommendations_cat(self, client):
        """Test getting product recommendations for cats"""
        response = client.get("/api/products/recommendations?pet_type=cat")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["products"]) > 0
    
    def test_get_product_recommendations_with_age(self, client):
        """Test product recommendations with age filter"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_age=puppy")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["products"]) > 0
    
    def test_get_product_recommendations_with_size(self, client):
        """Test product recommendations with size filter"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_size=large")
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_product_recommendations_invalid_pet_type(self, client):
        """Test product recommendations with invalid pet type"""
        response = client.get("/api/products/recommendations?pet_type=fish")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "pet_type must be 'dog', 'cat', or 'both'" in data["detail"]
    
    def test_get_product_recommendations_invalid_age(self, client):
        """Test product recommendations with invalid age"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_age=baby")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_product_recommendations_invalid_size(self, client):
        """Test product recommendations with invalid size"""
        response = client.get("/api/products/recommendations?pet_type=dog&pet_size=huge")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_get_product_recommendations_with_limit(self, client):
        """Test product recommendations with custom limit"""
        response = client.get("/api/products/recommendations?pet_type=dog&limit=3")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] <= 3


class TestRescueResourcesEndpoint:
    """Test curated rescue directory endpoint"""

    def test_rescue_resources_structure(self, client):
        """Response should include metadata and section counts"""
        response = client.get("/api/resources/rescues")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metadata" in data
        assert "states" in data and "massachusetts" in data["states"]
        assert len(data["states"]["massachusetts"]) >= 1
        assert "counts" in data
        assert data["counts"]["state_entries"] >= 1

    def test_rescue_resources_state_filter(self, client):
        """State query narrows payload to requested state"""
        response = client.get("/api/resources/rescues", params={"state": "MA"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert list(data["states"].keys()) in (["massachusetts"], [])
        if data["states"]:
            assert data["counts"]["state_groups"] == 1

    def test_rescue_resources_network_filter(self, client):
        """network_region query returns only matching corridor"""
        response = client.get("/api/resources/rescues", params={"network_region": "southern_source"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert list(data["national"].keys()) in (["southern_source"], [])
        if data["national"]:
            assert len(data["national"]["southern_source"]) >= 1

    def test_rescue_resources_breed_filter(self, client):
        """Breed filter restricts AKC network entries"""
        response = client.get("/api/resources/rescues", params={"breed": "Husky"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["akc_network"]
        assert all("husky" in entry["breed"].lower() for entry in data["akc_network"])

    def test_rescue_resources_counts_match_dataset(self, client):
        """Summary counts should mirror the source dataset"""
        response = client.get("/api/resources/rescues")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        expected_state_groups = len(RESCUE_DIRECTORY.get("states", {}))
        expected_state_entries = sum(len(entries) for entries in RESCUE_DIRECTORY.get("states", {}).values())
        expected_network_regions = len(RESCUE_DIRECTORY.get("national", {}))
        expected_network_entries = sum(len(entries) for entries in RESCUE_DIRECTORY.get("national", {}).values())
        expected_akc_entries = len(RESCUE_DIRECTORY.get("akc_network", []))

        counts = data.get("counts", {})
        assert counts.get("state_groups") == expected_state_groups
        assert counts.get("state_entries") == expected_state_entries
        assert counts.get("network_regions") == expected_network_regions
        assert counts.get("network_entries") == expected_network_entries
        assert counts.get("akc_entries") == expected_akc_entries
        assert data["metadata"]["version"] == RESCUE_DIRECTORY["metadata"]["version"]

    def test_rescue_resources_can_skip_counts(self, client):
        """include_counts=false should omit expensive aggregation"""
        response = client.get("/api/resources/rescues", params={"include_counts": "false"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "counts" not in data

    def test_rescue_resources_sets_etag_and_honors_conditional(self, client):
        """Endpoint should expose cache headers and support conditional GETs"""
        initial = client.get("/api/resources/rescues")
        assert initial.status_code == status.HTTP_200_OK
        etag = initial.headers.get("etag")
        cache_control = initial.headers.get("cache-control")
        assert etag, "ETag header should be present"
        assert cache_control and "max-age" in cache_control

        conditional = client.get(
            "/api/resources/rescues",
            headers={"if-none-match": etag}
        )
        assert conditional.status_code == status.HTTP_304_NOT_MODIFIED
        assert conditional.content == b""
        assert conditional.headers.get("etag") == etag


class TestErrorHandling:
    """Test error handling across endpoints"""
    
    def test_invalid_json_body(self, client):
        """Test handling of invalid JSON in request body"""
        response = client.post(
            "/api/success-stories",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_method_not_allowed(self, client):
        """Test method not allowed response"""
        response = client.delete("/api/animals")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
