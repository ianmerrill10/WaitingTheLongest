"""
Waiting The Longest™ - Test Configuration Fixtures
===================================================
Additional test fixtures for comprehensive testing.
"""

import pytest
from datetime import date, timedelta
from typing import Generator, Dict, Any
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.database import Base
from app.models import Animal, Shelter, SuccessStory, NewsletterSubscriber


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def populated_db(db_session: Session) -> Session:
    """Create a populated database with test data."""
    from tests.factories import (
        ShelterFactory,
        AnimalFactory,
        SuccessStoryFactory,
        NewsletterSubscriberFactory,
    )
    
    # Create shelters
    shelters = [ShelterFactory.create() for _ in range(5)]
    for shelter in shelters:
        db_shelter = Shelter(**shelter)
        db_session.add(db_shelter)
    db_session.commit()
    
    # Get shelter IDs
    shelter_ids = [s.id for s in db_session.query(Shelter).all()]
    
    # Create animals for each shelter
    for shelter_id in shelter_ids:
        for _ in range(10):
            animal_data = AnimalFactory.create()
            animal_data["shelter_id"] = shelter_id
            animal = Animal(**animal_data)
            db_session.add(animal)
    
    # Create success stories
    for _ in range(5):
        story_data = SuccessStoryFactory.create()
        story = SuccessStory(**story_data)
        db_session.add(story)
    
    # Create newsletter subscribers
    for _ in range(20):
        subscriber_data = NewsletterSubscriberFactory.create()
        subscriber = NewsletterSubscriber(**subscriber_data)
        db_session.add(subscriber)
    
    db_session.commit()
    
    return db_session


@pytest.fixture
def long_term_animals(db_session: Session) -> list:
    """Create animals with various wait times for testing sorting."""
    from tests.factories import AnimalFactory
    
    # Create a shelter first
    shelter = Shelter(
        name="Test Shelter",
        city="Test City",
        state="TS",
        email="test@shelter.org",
    )
    db_session.add(shelter)
    db_session.commit()
    
    # Create animals with specific wait times
    wait_times = [7, 30, 90, 180, 365, 500, 730]  # days
    animals = []
    
    for days in wait_times:
        intake_date = date.today() - timedelta(days=days)
        animal = Animal(
            name=f"Animal-{days}days",
            species="Dog",
            breed="Mixed",
            age="Adult",
            gender="Male",
            intake_date=intake_date,
            shelter_id=shelter.id,
        )
        db_session.add(animal)
        animals.append(animal)
    
    db_session.commit()
    db_session.refresh(shelter)
    
    return animals


# =============================================================================
# API Response Fixtures
# =============================================================================

@pytest.fixture
def mock_rescuegroups_response() -> Dict[str, Any]:
    """Mock response from RescueGroups API."""
    return {
        "data": [
            {
                "id": "12345",
                "type": "animals",
                "attributes": {
                    "name": "Buddy",
                    "species": {"name": "Dog"},
                    "breeds": {"primary": {"name": "Golden Retriever"}},
                    "ageGroup": "Adult",
                    "sex": "Male",
                    "descriptionText": "A friendly golden retriever looking for a home.",
                    "pictureThumbnailUrl": "https://example.com/photo.jpg",
                    "createdDate": "2023-01-15T00:00:00Z",
                },
                "relationships": {
                    "orgs": {
                        "data": [{"type": "orgs", "id": "org1"}]
                    }
                }
            }
        ],
        "included": [
            {
                "id": "org1",
                "type": "orgs",
                "attributes": {
                    "name": "Happy Tails Shelter",
                    "city": "Portland",
                    "state": "OR",
                    "email": "info@happytails.org",
                    "phone": "555-123-4567",
                    "website": "https://happytails.org",
                }
            }
        ],
        "meta": {
            "count": 1,
            "pageReturned": 1,
            "pages": 1,
        }
    }


@pytest.fixture
def mock_petfinder_response() -> Dict[str, Any]:
    """Mock response from Petfinder API (for future use)."""
    return {
        "animals": [
            {
                "id": 67890,
                "organization_id": "MA123",
                "url": "https://petfinder.com/dog/buddy-67890",
                "type": "Dog",
                "species": "Dog",
                "breeds": {
                    "primary": "Labrador Retriever",
                    "secondary": None,
                    "mixed": False,
                },
                "age": "Young",
                "gender": "Female",
                "size": "Medium",
                "name": "Luna",
                "description": "Sweet lab looking for a family.",
                "photos": [
                    {
                        "small": "https://dl5zpyw5k3jeb.cloudfront.net/photos/pets/67890/1/?bust=1234",
                        "medium": "https://dl5zpyw5k3jeb.cloudfront.net/photos/pets/67890/1/?bust=1234",
                        "large": "https://dl5zpyw5k3jeb.cloudfront.net/photos/pets/67890/1/?bust=1234",
                    }
                ],
                "status": "adoptable",
                "published_at": "2023-02-01T12:00:00+0000",
            }
        ],
        "pagination": {
            "count_per_page": 20,
            "total_count": 1,
            "current_page": 1,
            "total_pages": 1,
        }
    }


# =============================================================================
# Request/Response Fixtures
# =============================================================================

@pytest.fixture
def valid_newsletter_signup() -> Dict[str, Any]:
    """Valid newsletter signup request data."""
    return {
        "email": "newsubscriber@example.com",
        "name": "Test User",
        "preferences": {
            "species": ["dog", "cat"],
            "frequency": "weekly",
        }
    }


@pytest.fixture
def valid_animal_filter() -> Dict[str, Any]:
    """Valid animal filter parameters."""
    return {
        "species": "dog",
        "breed": "Golden Retriever",
        "age": "adult",
        "gender": "male",
        "min_days_waiting": 30,
        "state": "CA",
    }


# =============================================================================
# Performance Testing Fixtures
# =============================================================================

@pytest.fixture
def large_dataset(db_session: Session) -> Session:
    """Create a large dataset for performance testing."""
    from tests.factories import ShelterFactory, AnimalFactory
    
    # Create 50 shelters
    shelters = []
    for _ in range(50):
        shelter_data = ShelterFactory.create()
        shelter = Shelter(**shelter_data)
        db_session.add(shelter)
        shelters.append(shelter)
    
    db_session.commit()
    
    # Create 100 animals per shelter = 5000 total
    for shelter in shelters:
        for _ in range(100):
            animal_data = AnimalFactory.create()
            animal_data["shelter_id"] = shelter.id
            animal = Animal(**animal_data)
            db_session.add(animal)
    
    db_session.commit()
    
    return db_session


# =============================================================================
# Error Condition Fixtures
# =============================================================================

@pytest.fixture
def invalid_email() -> str:
    """Invalid email for testing validation."""
    return "not-an-email"


@pytest.fixture
def malicious_input() -> Dict[str, str]:
    """Potentially malicious input for security testing."""
    return {
        "sql_injection": "'; DROP TABLE animals; --",
        "xss_script": "<script>alert('xss')</script>",
        "path_traversal": "../../../etc/passwd",
        "long_string": "x" * 10000,
        "unicode_evil": "test\x00\x00hidden",
    }
