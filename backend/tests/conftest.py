"""
===============================================================================
Waiting The Longest™ - Test Configuration
===============================================================================
Pytest fixtures and configuration for testing.

This module provides:
- In-memory SQLite database for isolated testing
- Test client with proper dependency injection
- Sample data fixtures (animals, shelters, observations, success stories)
- Fixtures for testing various scenarios (empty DB, multiple animals, etc.)

Usage:
    def test_something(client, db_session, sample_animal):
        # client is the FastAPI TestClient
        # db_session is the SQLAlchemy session
        # sample_animal is a pre-created Animal instance

===============================================================================
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timezone, timedelta

# Set testing environment variable before importing app
os.environ["TESTING"] = "1"

from app.main import app
from app.database import Base, get_db
from app.models import Animal, Observation, Shelter, SuccessStory, SocialPromotion, AffiliateClick


# Use in-memory SQLite for tests - completely isolated from production
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # StaticPool reuses the same connection for all requests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    
    This fixture:
    - Creates all tables fresh for each test
    - Provides an isolated session
    - Cleans up (drops all tables) after each test
    """
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with database override.
    
    This fixture:
    - Overrides the database dependency with the test session
    - Provides a TestClient for making API requests
    - Cleans up after each test
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_rate_limiter():
    """Mock the rate limiter to avoid rate limit errors in tests"""
    with patch("slowapi.Limiter.limit", lambda *args, **kwargs: lambda f: f):
        yield


@pytest.fixture
def sample_shelter(db_session):
    """Create a sample shelter for testing"""
    shelter = Shelter(
        name="Test Animal Shelter",
        source="test",
        external_id="TEST001",
        city="Austin",
        state="TX",
        zip_code="78701",
        phone="512-555-1234",
        email="test@shelter.org",
        website="https://testshelter.org"
    )
    db_session.add(shelter)
    db_session.commit()
    db_session.refresh(shelter)
    return shelter


@pytest.fixture
def sample_animal(db_session):
    """
    Create a sample animal for testing.
    
    Creates a dog named "Max" that has been waiting 100 days.
    """
    # Create animal that has been waiting 100 days
    first_seen = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=100)
    
    animal = Animal(
        species="dog",
        canonical_name="Max",
        breed_primary="Labrador Retriever",
        breed_secondary="Mixed",
        color_primary="Black",
        age_group="adult",
        size="large",
        gender="male",
        status="available",
        first_seen_at=first_seen,
        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(animal)
    db_session.commit()
    db_session.refresh(animal)
    return animal


@pytest.fixture
def sample_animal_with_observation(db_session, sample_animal, sample_shelter):
    """
    Create an animal with an associated observation.
    
    This fixture builds on sample_animal and adds:
    - Full observation data with photos, description, etc.
    - Link to sample_shelter
    """
    observation = Observation(
        animal_id=sample_animal.id,
        shelter_id=sample_shelter.id,
        source="rescuegroups",
        external_id="RG12345",
        shelter_name=sample_shelter.name,
        name="Max",
        breed_primary="Labrador Retriever",
        description="Friendly and playful dog looking for a forever home!",
        photo_url="https://example.com/max.jpg",
        photo_gallery_json='["https://example.com/max1.jpg", "https://example.com/max2.jpg"]',
        city="Austin",
        state="TX",
        zip_code="78701",
        listing_url="https://rescuegroups.org/animal/12345",
        first_seen_at=sample_animal.first_seen_at,
        last_seen_at=sample_animal.last_seen_at
    )
    db_session.add(observation)
    db_session.commit()
    return sample_animal


@pytest.fixture
def multiple_animals(db_session):
    """
    Create multiple animals with varying wait times for testing.
    
    Creates:
    - Buddy (dog): 500 days waiting, available - LONGEST WAITING
    - Whiskers (cat): 200 days waiting, available
    - Luna (dog/puppy): 50 days waiting, available
    - Rocky (dog): 300 days, ADOPTED (should not appear in available searches)
    """
    animals = []
    
    # Animal waiting 500 days (longest)
    animal1 = Animal(
        species="dog",
        canonical_name="Buddy",
        breed_primary="German Shepherd",
        age_group="senior",
        size="large",
        gender="male",
        status="available",
        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=500),
        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    # Animal waiting 200 days
    animal2 = Animal(
        species="cat",
        canonical_name="Whiskers",
        breed_primary="Domestic Shorthair",
        age_group="adult",
        size="medium",
        gender="female",
        status="available",
        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=200),
        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    # Animal waiting 50 days
    animal3 = Animal(
        species="dog",
        canonical_name="Luna",
        breed_primary="Beagle",
        age_group="puppy",
        size="small",
        gender="female",
        status="available",
        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=50),
        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    # Adopted animal (should not appear in available searches)
    animal4 = Animal(
        species="dog",
        canonical_name="Rocky",
        breed_primary="Bulldog",
        age_group="adult",
        size="medium",
        gender="male",
        status="adopted",
        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=300),
        last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    for animal in [animal1, animal2, animal3, animal4]:
        db_session.add(animal)
        animals.append(animal)
    
    db_session.commit()
    for animal in animals:
        db_session.refresh(animal)
    
    return animals


@pytest.fixture
def multiple_animals_with_observations(db_session, multiple_animals, sample_shelter):
    """
    Create multiple animals with observations for testing state filtering.
    """
    for animal in multiple_animals:
        observation = Observation(
            animal_id=animal.id,
            shelter_id=sample_shelter.id,
            source="test",
            external_id=f"TEST{animal.id}",
            shelter_name=sample_shelter.name,
            name=animal.canonical_name,
            city=sample_shelter.city,
            state=sample_shelter.state,
            first_seen_at=animal.first_seen_at,
            last_seen_at=animal.last_seen_at
        )
        db_session.add(observation)
    
    db_session.commit()
    return multiple_animals


@pytest.fixture
def sample_success_story(db_session, sample_animal):
    """
    Create a sample success story for testing.
    
    Creates an approved (visible) success story linked to sample_animal.
    """
    story = SuccessStory(
        animal_id=sample_animal.id,
        pet_name="Max",
        adopter_name="John Smith",
        story_text="After 100 days of waiting, Max finally found his forever home! He's now the happiest dog in Texas, loves playing fetch in the backyard, and has become best friends with our cat.",
        days_waited=100,
        adoption_date=datetime.now(timezone.utc).replace(tzinfo=None),
        is_approved=True,
        is_featured=False,
        contact_email="john@example.com"
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)
    return story


@pytest.fixture
def featured_success_story(db_session):
    """Create a featured success story (no animal link)"""
    story = SuccessStory(
        pet_name="Featured Pet",
        adopter_name="Featured Adopter",
        story_text="This is a featured success story that should appear first in trending stories.",
        days_waited=365,
        adoption_date=datetime.now(timezone.utc).replace(tzinfo=None),
        is_approved=True,
        is_featured=True,
        contact_email="featured@example.com"
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)
    return story


@pytest.fixture
def unapproved_success_story(db_session, sample_animal):
    """Create an unapproved success story (should not be visible)"""
    story = SuccessStory(
        animal_id=sample_animal.id,
        pet_name="Pending Max",
        story_text="This story is pending approval and should not appear in public queries.",
        days_waited=50,
        is_approved=False,
        is_featured=False
    )
    db_session.add(story)
    db_session.commit()
    db_session.refresh(story)
    return story


@pytest.fixture
def sample_social_promotion(db_session, sample_animal):
    """Create a sample social promotion for testing"""
    promotion = SocialPromotion(
        animal_id=sample_animal.id,
        platform="tiktok",
        status="posted",
        caption="Meet Max! 100 days waiting for love 🐕❤️",
        post_url="https://tiktok.com/@waitingthelongest/video/123",
        views=10000,
        likes=500,
        shares=50,
        comments=25
    )
    db_session.add(promotion)
    db_session.commit()
    db_session.refresh(promotion)
    return promotion


@pytest.fixture
def sample_affiliate_click(db_session, sample_animal):
    """Create a sample affiliate click for testing"""
    click = AffiliateClick(
        product_id="dog-food-test",
        affiliate_program="amazon",
        source_page="animal_detail",
        animal_id=sample_animal.id,
        ip_hash="abc123def456",
        clicked_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db_session.add(click)
    db_session.commit()
    db_session.refresh(click)
    return click


@pytest.fixture
def animal_with_phash(db_session):
    """Create an animal with a perceptual hash for deduplication testing"""
    animal = Animal(
        species="dog",
        canonical_name="PhotoDog",
        breed_primary="Poodle",
        status="available",
        photo_phash="0123456789abcdef",
        first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    )
    db_session.add(animal)
    db_session.commit()
    db_session.refresh(animal)
    return animal
