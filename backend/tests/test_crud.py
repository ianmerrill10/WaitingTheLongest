"""
===============================================================================
Waiting The Longest™ - CRUD Operation Tests
===============================================================================
Comprehensive tests for database operations and business logic.

Tests:
- paginate_animals: Pagination, filtering, sorting
- get_animal_detail: Retrieve single animal with all relations
- create_success_story: Submit new success stories
- find_duplicate_animal: Deduplication logic (name, breed, phash)
- get_trending_stories: Featured story retrieval
- get_platform_stats: Statistics calculations
- merge_animal_observation: Adding observations to existing animals

===============================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta

from backend.app.crud import (
    create_success_story,
    find_duplicate_animal,
    get_animal_detail,
    get_platform_stats,
    get_trending_stories,
    merge_animal_observation,
    paginate_animals,
)
from backend.app.models import Animal, Observation, SuccessStory
from backend.app.schemas import SuccessStoryCreate


class TestPaginateAnimals:
    """Test animal pagination and filtering"""
    
    def test_paginate_empty(self, db_session):
        """Test pagination with no animals"""
        result = paginate_animals(db_session)
        assert result.total == 0
        assert result.items == []
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 0
        assert result.has_next == False
        assert result.has_prev == False
    
    def test_paginate_with_animals(self, db_session, multiple_animals):
        """Test basic pagination"""
        result = paginate_animals(db_session)
        # Should return 3 available animals (not the adopted one)
        assert result.total == 3
        assert len(result.items) == 3
    
    def test_paginate_species_filter_dog(self, db_session, multiple_animals):
        """Test filtering by species - dogs"""
        result = paginate_animals(db_session, species="dog")
        assert result.total == 2  # Buddy and Luna (not Rocky who is adopted)
        for item in result.items:
            assert item.species == "dog"
    
    def test_paginate_species_filter_cat(self, db_session, multiple_animals):
        """Test filtering by species - cats"""
        result = paginate_animals(db_session, species="cat")
        assert result.total == 1
        assert result.items[0].canonical_name == "Whiskers"
    
    def test_paginate_status_filter(self, db_session, multiple_animals):
        """Test filtering by status"""
        # Available (default)
        result = paginate_animals(db_session, status="available")
        assert result.total == 3
        
        # Adopted
        result = paginate_animals(db_session, status="adopted")
        assert result.total == 1
        assert result.items[0].canonical_name == "Rocky"
    
    def test_paginate_breed_filter(self, db_session, multiple_animals):
        """Test filtering by breed (partial match)"""
        result = paginate_animals(db_session, breed="Shepherd", status="available")
        assert result.total == 1
        assert result.items[0].canonical_name == "Buddy"
    
    def test_paginate_age_group_filter(self, db_session, multiple_animals):
        """Test filtering by age group"""
        result = paginate_animals(db_session, age_group="senior")
        assert result.total == 1
        assert result.items[0].canonical_name == "Buddy"
        
        result = paginate_animals(db_session, age_group="puppy")
        assert result.total == 1
        assert result.items[0].canonical_name == "Luna"
    
    def test_paginate_size_filter(self, db_session, multiple_animals):
        """Test filtering by size"""
        result = paginate_animals(db_session, size="large")
        assert result.total == 1
        assert result.items[0].canonical_name == "Buddy"
    
    def test_paginate_gender_filter(self, db_session, multiple_animals):
        """Test filtering by gender"""
        result = paginate_animals(db_session, gender="female")
        assert result.total == 2  # Whiskers and Luna
    
    def test_paginate_combined_filters(self, db_session, multiple_animals):
        """Test combining multiple filters"""
        result = paginate_animals(
            db_session, 
            species="dog", 
            gender="female",
            age_group="puppy"
        )
        assert result.total == 1
        assert result.items[0].canonical_name == "Luna"
    
    def test_paginate_default_sort_days_waiting_desc(self, db_session, multiple_animals):
        """Test default sorting by days_waiting desc"""
        result = paginate_animals(db_session, sort_by="days_waiting", sort_order="desc")
        # First animal should be longest waiting
        assert result.items[0].canonical_name == "Buddy"
        assert result.items[0].days_waiting >= 499
        # Verify order
        for i in range(len(result.items) - 1):
            assert result.items[i].days_waiting >= result.items[i + 1].days_waiting
    
    def test_paginate_sort_days_waiting_asc(self, db_session, multiple_animals):
        """Test sorting by days_waiting ascending"""
        result = paginate_animals(db_session, sort_by="days_waiting", sort_order="asc")
        # First animal should be shortest waiting
        assert result.items[0].canonical_name == "Luna"
    
    def test_paginate_sort_by_name(self, db_session, multiple_animals):
        """Test sorting by name"""
        result = paginate_animals(db_session, sort_by="name", sort_order="asc")
        names = [item.canonical_name for item in result.items]
        assert names == sorted(names)
    
    def test_paginate_pagination_params(self, db_session, multiple_animals):
        """Test pagination parameters"""
        result = paginate_animals(db_session, page=1, page_size=2)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 2
        assert result.has_next == True
        assert result.has_prev == False
        
        # Second page
        result = paginate_animals(db_session, page=2, page_size=2)
        assert len(result.items) == 1
        assert result.has_next == False
        assert result.has_prev == True
    
    def test_paginate_page_beyond_data(self, db_session, multiple_animals):
        """Test pagination with page number beyond available data"""
        result = paginate_animals(db_session, page=10, page_size=20)
        assert len(result.items) == 0
        assert result.total == 3
    
    def test_paginate_state_filter(self, db_session, multiple_animals_with_observations):
        """Test filtering by state"""
        result = paginate_animals(db_session, state="TX")
        # All test animals have TX observations
        assert result.total >= 1
    
    def test_paginate_item_structure(self, db_session, sample_animal_with_observation):
        """Test that paginated items have correct structure"""
        result = paginate_animals(db_session)
        item = result.items[0]
        
        # Check all expected fields
        assert hasattr(item, 'id')
        assert hasattr(item, 'species')
        assert hasattr(item, 'canonical_name')
        assert hasattr(item, 'breed_primary')
        assert hasattr(item, 'age_group')
        assert hasattr(item, 'size')
        assert hasattr(item, 'gender')
        assert hasattr(item, 'status')
        assert hasattr(item, 'days_waiting')
        assert hasattr(item, 'first_seen_at')
        assert hasattr(item, 'photo_url')
        assert hasattr(item, 'city')
        assert hasattr(item, 'state')


class TestGetAnimalDetail:
    """Test getting animal details"""
    
    def test_get_existing_animal(self, db_session, sample_animal_with_observation):
        """Test getting existing animal"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        assert result is not None
        assert result.canonical_name == "Max"
        assert result.breed_primary == "Labrador Retriever"
        assert len(result.observations) == 1
    
    def test_get_nonexistent_animal(self, db_session):
        """Test getting non-existent animal returns None"""
        result = get_animal_detail(db_session, 99999)
        assert result is None
    
    def test_get_animal_with_photos(self, db_session, sample_animal_with_observation):
        """Test that photos are collected from observations"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        assert len(result.photos) > 0
        # Check primary photo is included
        assert any("max.jpg" in photo for photo in result.photos)
    
    def test_get_animal_with_description(self, db_session, sample_animal_with_observation):
        """Test that description is pulled from observation"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        assert result.description is not None
        assert "Friendly and playful" in result.description
    
    def test_get_animal_with_adoption_url(self, db_session, sample_animal_with_observation):
        """Test that adoption URL is included"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        assert result.adoption_url is not None
        assert "rescuegroups.org" in result.adoption_url
    
    def test_get_animal_with_shelter_info(self, db_session, sample_animal_with_observation):
        """Test that shelter info is included"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        assert result.shelter_info is not None
        assert result.shelter_info["name"] == "Test Animal Shelter"
        assert result.shelter_info["state"] == "TX"
    
    def test_get_animal_days_waiting(self, db_session, sample_animal_with_observation):
        """Test days_waiting calculation in detail response"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        # sample_animal was created 100 days ago
        assert result.days_waiting >= 99
        assert result.days_waiting <= 101
    
    def test_get_animal_observations_structure(self, db_session, sample_animal_with_observation):
        """Test observation structure in detail response"""
        result = get_animal_detail(db_session, sample_animal_with_observation.id)
        obs = result.observations[0]
        
        assert obs.source == "rescuegroups"
        assert obs.shelter_name == "Test Animal Shelter"
        assert obs.city == "Austin"
        assert obs.state == "TX"
        assert obs.photo_url is not None


class TestSuccessStories:
    """Test success story operations"""
    
    def test_create_story_full(self, db_session, sample_animal):
        """Test creating a success story with all fields"""
        story_data = SuccessStoryCreate(
            pet_name="Max",
            adopter_name="Test User",
            story_text="This is a test story that is long enough to meet the minimum character requirement for validation.",
            days_waited=100,
            animal_id=sample_animal.id,
            contact_email="test@example.com",
            adoption_date=datetime.now(timezone.utc).replace(tzinfo=None),
            photo_urls=["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"]
        )
        
        result = create_success_story(db_session, story_data)
        assert result.id is not None
        assert result.pet_name == "Max"
        assert result.adopter_name == "Test User"
        assert result.days_waited == 100
        assert result.is_approved == False  # Should require moderation
        assert result.is_featured == False
        assert result.animal_id == sample_animal.id
    
    def test_create_story_minimal(self, db_session):
        """Test creating a success story with minimal fields"""
        story_data = SuccessStoryCreate(
            pet_name="Minimal Pet",
            story_text="This is a minimal story that meets the character requirement for testing.",
            days_waited=30
        )
        
        result = create_success_story(db_session, story_data)
        assert result.id is not None
        assert result.pet_name == "Minimal Pet"
        assert result.animal_id is None
        assert result.adopter_name is None
    
    def test_get_trending_stories_approved_only(self, db_session, sample_success_story, unapproved_success_story):
        """Test that only approved stories are returned"""
        result = get_trending_stories(db_session, limit=10)
        assert len(result) == 1
        assert result[0].pet_name == "Max"
    
    def test_get_trending_stories_featured_first(self, db_session, sample_success_story, featured_success_story):
        """Test that featured stories come first"""
        result = get_trending_stories(db_session, limit=10)
        # Featured story should come first
        assert result[0].pet_name == "Featured Pet"
        assert result[0].is_featured == True
    
    def test_get_trending_stories_sorted_by_days_waited(self, db_session):
        """Test stories sorted by days waited after featured"""
        # Create multiple approved non-featured stories
        story1 = SuccessStory(
            pet_name="Story1",
            story_text="Story with 10 days",
            days_waited=10,
            is_approved=True,
            is_featured=False
        )
        story2 = SuccessStory(
            pet_name="Story2",
            story_text="Story with 100 days",
            days_waited=100,
            is_approved=True,
            is_featured=False
        )
        db_session.add_all([story1, story2])
        db_session.commit()
        
        result = get_trending_stories(db_session, limit=10)
        # Higher days_waited should come first
        assert result[0].days_waited >= result[1].days_waited
    
    def test_get_trending_stories_limit(self, db_session):
        """Test limit parameter"""
        # Create multiple stories
        for i in range(15):
            story = SuccessStory(
                pet_name=f"Pet{i}",
                story_text=f"Story {i}",
                days_waited=i * 10,
                is_approved=True
            )
            db_session.add(story)
        db_session.commit()
        
        result = get_trending_stories(db_session, limit=5)
        assert len(result) == 5
    
    def test_get_trending_stories_with_animal(self, db_session, sample_success_story):
        """Test that animal relationship is loaded"""
        result = get_trending_stories(db_session, limit=10)
        assert result[0].animal is not None
        assert result[0].animal.canonical_name == "Max"


class TestDeduplication:
    """Test animal deduplication logic"""
    
    def test_find_duplicate_by_name_species(self, db_session, sample_animal):
        """Test finding duplicate by name and species"""
        result = find_duplicate_animal(
            db_session,
            name="Max",
            species="dog"
        )
        assert result is not None
        assert result.id == sample_animal.id
    
    def test_find_duplicate_case_insensitive(self, db_session, sample_animal):
        """Test that name matching is case insensitive"""
        result = find_duplicate_animal(
            db_session,
            name="MAX",
            species="dog"
        )
        assert result is not None
        assert result.id == sample_animal.id
        
        result = find_duplicate_animal(
            db_session,
            name="max",
            species="dog"
        )
        assert result is not None
    
    def test_find_duplicate_by_name_species_breed(self, db_session, sample_animal):
        """Test finding duplicate with breed match"""
        result = find_duplicate_animal(
            db_session,
            name="Max",
            species="dog",
            breed="Labrador Retriever"
        )
        assert result is not None
        assert result.id == sample_animal.id
    
    def test_find_duplicate_by_phash(self, db_session, animal_with_phash):
        """Test finding duplicate by perceptual hash"""
        result = find_duplicate_animal(
            db_session,
            name="Different Name",  # Name doesn't matter if phash matches
            species="dog",
            photo_phash="0123456789abcdef"
        )
        assert result is not None
        assert result.id == animal_with_phash.id
    
    def test_find_duplicate_phash_priority(self, db_session, sample_animal, animal_with_phash):
        """Test that phash match takes priority"""
        result = find_duplicate_animal(
            db_session,
            name="PhotoDog",
            species="dog",
            photo_phash="0123456789abcdef"
        )
        # Should find phash match first
        assert result is not None
        assert result.id == animal_with_phash.id
    
    def test_no_duplicate_found(self, db_session, sample_animal):
        """Test when no duplicate exists"""
        result = find_duplicate_animal(
            db_session,
            name="Completely Different Name",
            species="dog"
        )
        assert result is None
    
    def test_no_duplicate_different_species(self, db_session, sample_animal):
        """Test that different species doesn't match"""
        result = find_duplicate_animal(
            db_session,
            name="Max",
            species="cat"  # sample_animal is a dog
        )
        assert result is None
    
    def test_no_duplicate_empty_db(self, db_session):
        """Test finding duplicate in empty database"""
        result = find_duplicate_animal(
            db_session,
            name="Any Name",
            species="dog"
        )
        assert result is None


class TestMergeAnimalObservation:
    """Test merging observations into existing animals"""
    
    def test_merge_observation(self, db_session, sample_animal):
        """Test adding observation to existing animal"""
        observation_data = {
            "source": "adoptapet",
            "external_id": "AP12345",
            "shelter_name": "New Shelter",
            "name": "Max",
            "city": "Dallas",
            "state": "TX"
        }
        
        result = merge_animal_observation(db_session, sample_animal, observation_data)
        
        assert result.id is not None
        assert result.animal_id == sample_animal.id
        assert result.source == "adoptapet"
        assert result.city == "Dallas"
    
    def test_merge_updates_last_seen(self, db_session, sample_animal):
        """Test that merging updates animal's last_seen_at"""
        original_last_seen = sample_animal.last_seen_at
        
        observation_data = {
            "source": "test",
            "external_id": "TEST123",
            "shelter_name": "Test Shelter",
            "name": "Max"
        }
        
        merge_animal_observation(db_session, sample_animal, observation_data)
        db_session.refresh(sample_animal)
        
        # last_seen_at should be updated
        assert sample_animal.last_seen_at >= original_last_seen
    
    def test_merge_updates_name_if_missing(self, db_session):
        """Test that merge updates animal name if it was missing"""
        animal = Animal(
            species="dog",
            canonical_name=None,  # No name
            status="available"
        )
        db_session.add(animal)
        db_session.commit()
        
        observation_data = {
            "source": "test",
            "external_id": "TEST123",
            "shelter_name": "Test Shelter",
            "name": "Discovered Name"
        }
        
        merge_animal_observation(db_session, animal, observation_data)
        db_session.refresh(animal)
        
        assert animal.canonical_name == "Discovered Name"


class TestPlatformStats:
    """Test platform statistics"""
    
    def test_stats_empty_db(self, db_session):
        """Test stats with empty database"""
        result = get_platform_stats(db_session)
        assert result["total_animals"] == 0
        assert result["available_animals"] == 0
        assert result["success_stories"] == 0
        assert result["longest_wait_days"] == 0
    
    def test_stats_total_animals(self, db_session, multiple_animals):
        """Test total animals count"""
        result = get_platform_stats(db_session)
        assert result["total_animals"] == 4  # All animals
    
    def test_stats_available_animals(self, db_session, multiple_animals):
        """Test available animals count"""
        result = get_platform_stats(db_session)
        assert result["available_animals"] == 3  # Only available
    
    def test_stats_longest_wait(self, db_session, multiple_animals):
        """Test longest waiting calculation"""
        result = get_platform_stats(db_session)
        assert result["longest_wait_days"] >= 499  # Buddy has been waiting ~500 days
    
    def test_stats_success_stories_count(self, db_session, sample_success_story):
        """Test success story count (only approved)"""
        result = get_platform_stats(db_session)
        assert result["success_stories"] == 1
    
    def test_stats_average_wait(self, db_session, multiple_animals):
        """Test average wait time calculation"""
        result = get_platform_stats(db_session)
        # Average of 500, 200, 50 = 250 days (approximately)
        assert result["average_wait_days"] > 0
    
    def test_stats_with_mixed_data(self, db_session, multiple_animals, sample_success_story):
        """Test stats with comprehensive data"""
        result = get_platform_stats(db_session)
        
        # Verify all fields are present
        assert "total_animals" in result
        assert "available_animals" in result
        assert "average_wait_days" in result
        assert "longest_wait_days" in result
        assert "success_stories" in result
