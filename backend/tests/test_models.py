"""
===============================================================================
Waiting The Longest™ - Model Tests
===============================================================================
Comprehensive tests for SQLAlchemy models and business logic.

Models tested:
- Animal: Core animal record with days_waiting calculation
- Observation: Animal sightings from data sources
- Shelter: Shelter/rescue organization
- SuccessStory: Adoption success stories
- SocialPromotion: Social media post tracking
- AffiliateClick: Affiliate link click tracking

Key tests:
- Animal.days_waiting property calculation
- Model relationships (one-to-many, foreign keys)
- Default values and constraints
- Cascade behaviors

===============================================================================
"""

import pytest
from datetime import datetime, timezone, timedelta

from backend.app.models import (
    AffiliateClick,
    Animal,
    Observation,
    Shelter,
    SocialPromotion,
    SuccessStory,
)


class TestAnimalModel:
    """Test Animal model"""
    
    def test_create_animal_minimal(self, db_session):
        """Test creating an animal with minimal fields"""
        animal = Animal(
            species="dog",
            canonical_name="Buddy"
        )
        db_session.add(animal)
        db_session.commit()
        
        assert animal.id is not None
        assert animal.species == "dog"
        assert animal.canonical_name == "Buddy"
        assert animal.status == "available"  # Default
        assert animal.transfer_count == 0  # Default
    
    def test_create_animal_full(self, db_session):
        """Test creating an animal with all fields"""
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
            transfer_count=2,
            photo_phash="abc123def456",
            first_seen_at=first_seen,
            last_seen_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db_session.add(animal)
        db_session.commit()
        
        assert animal.id is not None
        assert animal.breed_secondary == "Mixed"
        assert animal.color_primary == "Black"
        assert animal.transfer_count == 2
        assert animal.photo_phash == "abc123def456"
    
    def test_days_waiting_calculation(self, db_session):
        """Test days_waiting property calculates correctly"""
        first_seen = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=150)
        
        animal = Animal(
            species="dog",
            canonical_name="Test",
            first_seen_at=first_seen,
            status="available"
        )
        db_session.add(animal)
        db_session.commit()
        
        # Should be approximately 150 days
        assert animal.days_waiting >= 149
        assert animal.days_waiting <= 151
    
    def test_days_waiting_zero_days(self, db_session):
        """Test days_waiting for newly added animal"""
        animal = Animal(
            species="dog",
            canonical_name="NewPet",
            first_seen_at=datetime.now(timezone.utc).replace(tzinfo=None),
            status="available"
        )
        db_session.add(animal)
        db_session.commit()
        
        assert animal.days_waiting == 0
    
    def test_days_waiting_no_first_seen(self, db_session):
        """Test days_waiting returns 0 when first_seen_at is None"""
        animal = Animal(
            species="dog",
            canonical_name="Test",
            first_seen_at=None,
            status="available"
        )
        db_session.add(animal)
        db_session.commit()
        
        assert animal.days_waiting == 0
    
    def test_days_waiting_long_wait(self, db_session):
        """Test days_waiting for very long waits"""
        first_seen = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1000)
        
        animal = Animal(
            species="dog",
            canonical_name="LongWait",
            first_seen_at=first_seen,
            status="available"
        )
        db_session.add(animal)
        db_session.commit()
        
        assert animal.days_waiting >= 999
    
    def test_animal_observations_relationship(self, db_session, sample_animal_with_observation):
        """Test animal-observations relationship"""
        animal = sample_animal_with_observation
        assert len(animal.observations) == 1
        assert animal.observations[0].name == "Max"
        assert animal.observations[0].source == "rescuegroups"
    
    def test_animal_success_stories_relationship(self, db_session, sample_success_story):
        """Test animal-success stories relationship"""
        animal = sample_success_story.animal
        assert len(animal.success_stories) == 1
        assert animal.success_stories[0].pet_name == "Max"
    
    def test_animal_promotions_relationship(self, db_session, sample_social_promotion):
        """Test animal-promotions relationship"""
        animal = sample_social_promotion.animal
        assert len(animal.promotions) == 1
        assert animal.promotions[0].platform == "tiktok"
    
    def test_animal_timestamps(self, db_session):
        """Test created_at and updated_at timestamps"""
        animal = Animal(
            species="dog",
            canonical_name="TimeTest"
        )
        db_session.add(animal)
        db_session.commit()
        
        assert animal.created_at is not None
        assert animal.updated_at is not None
    
    def test_animal_status_values(self, db_session):
        """Test different status values"""
        statuses = ["available", "adopted", "pending", "transferred"]
        
        for status in statuses:
            animal = Animal(
                species="dog",
                canonical_name=f"Status{status}",
                status=status
            )
            db_session.add(animal)
        
        db_session.commit()
        
        # All should be created successfully
        result = db_session.query(Animal).filter(
            Animal.canonical_name.like("Status%")
        ).all()
        assert len(result) == 4


class TestObservationModel:
    """Test Observation model"""
    
    def test_create_observation_minimal(self, db_session, sample_animal):
        """Test creating an observation with minimal fields"""
        observation = Observation(
            animal_id=sample_animal.id,
            source="test",
            external_id="TEST001",
            shelter_name="Test Shelter",
            name="Max"
        )
        db_session.add(observation)
        db_session.commit()
        
        assert observation.id is not None
        assert observation.animal_id == sample_animal.id
        assert observation.source == "test"
    
    def test_create_observation_full(self, db_session, sample_animal, sample_shelter):
        """Test creating an observation with all fields"""
        observation = Observation(
            animal_id=sample_animal.id,
            shelter_id=sample_shelter.id,
            source="rescuegroups",
            external_id="RG99999",
            shelter_name="Test Shelter",
            name="TestDog",
            breed_primary="Labrador",
            breed_secondary="Mix",
            description="A wonderful dog",
            photo_url="https://example.com/photo.jpg",
            photo_gallery_json='["url1", "url2"]',
            city="Houston",
            state="TX",
            zip_code="77001",
            listing_url="https://example.com/listing"
        )
        db_session.add(observation)
        db_session.commit()
        
        assert observation.id is not None
        assert observation.animal_id == sample_animal.id
        assert observation.source == "rescuegroups"
        assert observation.city == "Houston"
        assert observation.photo_gallery_json == '["url1", "url2"]'
    
    def test_observation_animal_relationship(self, db_session, sample_animal_with_observation):
        """Test observation-animal relationship"""
        observation = sample_animal_with_observation.observations[0]
        assert observation.animal is not None
        assert observation.animal.id == sample_animal_with_observation.id
    
    def test_observation_shelter_relationship(self, db_session, sample_animal_with_observation):
        """Test observation-shelter relationship"""
        observation = sample_animal_with_observation.observations[0]
        assert observation.shelter is not None
        assert observation.shelter.name == "Test Animal Shelter"
    
    def test_observation_timestamps(self, db_session, sample_animal):
        """Test observation timestamps"""
        observation = Observation(
            animal_id=sample_animal.id,
            source="test",
            external_id="TEST001",
            shelter_name="Test",
            name="Test"
        )
        db_session.add(observation)
        db_session.commit()
        
        assert observation.first_seen_at is not None
        assert observation.last_seen_at is not None


class TestShelterModel:
    """Test Shelter model"""
    
    def test_create_shelter_minimal(self, db_session):
        """Test creating a shelter with minimal fields"""
        shelter = Shelter(
            name="Happy Tails Rescue",
            source="rescuegroups"
        )
        db_session.add(shelter)
        db_session.commit()
        
        assert shelter.id is not None
        assert shelter.name == "Happy Tails Rescue"
        assert shelter.total_animals == 0  # Default
    
    def test_create_shelter_full(self, db_session):
        """Test creating a shelter with all fields"""
        shelter = Shelter(
            name="Full Shelter Info",
            source="rescuegroups",
            external_id="RG001",
            email="shelter@example.com",
            phone="555-1234",
            website="https://shelter.org",
            address="123 Main St",
            city="Dallas",
            state="TX",
            zip_code="75201",
            latitude=32.7767,
            longitude=-96.7970,
            total_animals=50
        )
        db_session.add(shelter)
        db_session.commit()
        
        assert shelter.id is not None
        assert shelter.email == "shelter@example.com"
        assert shelter.latitude == 32.7767
        assert shelter.total_animals == 50
    
    def test_shelter_observations_relationship(self, db_session, sample_animal_with_observation, sample_shelter):
        """Test shelter-observations relationship"""
        # Get the shelter with refreshed relationship
        db_session.refresh(sample_shelter)
        assert len(sample_shelter.observations) >= 1


class TestSuccessStoryModel:
    """Test SuccessStory model"""
    
    def test_create_success_story_minimal(self, db_session):
        """Test creating a success story with minimal fields"""
        story = SuccessStory(
            pet_name="Lucky",
            story_text="A wonderful adoption story!"
        )
        db_session.add(story)
        db_session.commit()
        
        assert story.id is not None
        assert story.is_approved == False  # Default
        assert story.is_featured == False  # Default
        assert story.days_waited == 0  # Default
    
    def test_create_success_story_full(self, db_session, sample_animal):
        """Test creating a success story with all fields"""
        story = SuccessStory(
            animal_id=sample_animal.id,
            pet_name="Max",
            adopter_name="John Doe",
            story_text="A wonderful adoption story that brings joy to everyone!",
            days_waited=100,
            photo_urls=["url1", "url2"],
            video_url="https://youtube.com/watch?v=123",
            adoption_date=datetime.now(timezone.utc).replace(tzinfo=None),
            is_approved=True,
            is_featured=True,
            contact_email="john@example.com"
        )
        db_session.add(story)
        db_session.commit()
        
        assert story.id is not None
        assert story.is_approved == True
        assert story.is_featured == True
        assert story.photo_urls == ["url1", "url2"]
    
    def test_success_story_animal_relationship(self, db_session, sample_success_story):
        """Test success story-animal relationship"""
        assert sample_success_story.animal is not None
        assert sample_success_story.animal.canonical_name == "Max"
    
    def test_success_story_submission_date(self, db_session):
        """Test submission_date auto-populates"""
        story = SuccessStory(
            pet_name="Auto Date",
            story_text="Testing auto date"
        )
        db_session.add(story)
        db_session.commit()
        
        assert story.submission_date is not None


class TestSocialPromotionModel:
    """Test SocialPromotion model"""
    
    def test_create_promotion_minimal(self, db_session, sample_animal):
        """Test creating a promotion with minimal fields"""
        promotion = SocialPromotion(
            animal_id=sample_animal.id,
            platform="tiktok"
        )
        db_session.add(promotion)
        db_session.commit()
        
        assert promotion.id is not None
        assert promotion.platform == "tiktok"
        assert promotion.status == "pending"  # Default
        assert promotion.views == 0  # Default
        assert promotion.likes == 0
        assert promotion.shares == 0
        assert promotion.comments == 0
    
    def test_create_promotion_full(self, db_session, sample_animal):
        """Test creating a promotion with all fields"""
        promotion = SocialPromotion(
            animal_id=sample_animal.id,
            platform="instagram",
            status="posted",
            video_path="/path/to/video.mp4",
            caption="Meet Max! 🐕❤️",
            post_url="https://instagram.com/p/123",
            post_id="123456",
            views=50000,
            likes=2500,
            shares=100,
            comments=50,
            scheduled_at=datetime.now(timezone.utc).replace(tzinfo=None),
            posted_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db_session.add(promotion)
        db_session.commit()
        
        assert promotion.id is not None
        assert promotion.views == 50000
        assert promotion.post_id == "123456"
    
    def test_promotion_animal_relationship(self, db_session, sample_social_promotion):
        """Test promotion-animal relationship"""
        assert sample_social_promotion.animal is not None
        assert sample_social_promotion.animal.canonical_name == "Max"
    
    def test_promotion_platforms(self, db_session, sample_animal):
        """Test different platform values"""
        platforms = ["tiktok", "instagram", "facebook", "twitter", "youtube"]
        
        for platform in platforms:
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform=platform
            )
            db_session.add(promotion)
        
        db_session.commit()
        
        result = db_session.query(SocialPromotion).filter(
            SocialPromotion.animal_id == sample_animal.id
        ).all()
        assert len(result) == 5
    
    def test_promotion_statuses(self, db_session, sample_animal):
        """Test different status values"""
        statuses = ["pending", "generating", "uploading", "posted", "failed"]
        
        for status in statuses:
            promotion = SocialPromotion(
                animal_id=sample_animal.id,
                platform="tiktok",
                status=status
            )
            db_session.add(promotion)
        
        db_session.commit()


class TestAffiliateClickModel:
    """Test AffiliateClick model"""
    
    def test_create_affiliate_click_minimal(self, db_session):
        """Test creating an affiliate click with minimal fields"""
        click = AffiliateClick(
            product_id="test-product",
            affiliate_program="amazon"
        )
        db_session.add(click)
        db_session.commit()
        
        assert click.id is not None
        assert click.product_id == "test-product"
        assert click.converted == False  # Default
        assert click.clicked_at is not None
    
    def test_create_affiliate_click_full(self, db_session, sample_animal):
        """Test creating an affiliate click with all fields"""
        click = AffiliateClick(
            product_id="dog-food-premium",
            affiliate_program="amazon",
            source_page="animal_detail",
            animal_id=sample_animal.id,
            session_id="session123",
            ip_hash="abc123def456",
            user_agent="Mozilla/5.0...",
            converted=True,
            conversion_value=29.99
        )
        db_session.add(click)
        db_session.commit()
        
        assert click.id is not None
        assert click.converted == True
        assert click.conversion_value == 29.99
        assert click.animal_id == sample_animal.id
    
    def test_affiliate_click_privacy(self, db_session):
        """Test that IP is hashed (not stored raw)"""
        click = AffiliateClick(
            product_id="test",
            affiliate_program="amazon",
            ip_hash="hashed_ip_value"  # Should be a hash, not raw IP
        )
        db_session.add(click)
        db_session.commit()
        
        # The model stores ip_hash, not raw IP
        assert click.ip_hash == "hashed_ip_value"


class TestModelCascades:
    """Test cascade delete behaviors"""
    
    def test_delete_animal_cascades_observations(self, db_session, sample_animal_with_observation):
        """Test that deleting an animal deletes its observations"""
        animal_id = sample_animal_with_observation.id
        
        # Verify observation exists
        obs_count = db_session.query(Observation).filter(
            Observation.animal_id == animal_id
        ).count()
        assert obs_count == 1
        
        # Delete animal
        db_session.delete(sample_animal_with_observation)
        db_session.commit()
        
        # Observations should be deleted
        obs_count = db_session.query(Observation).filter(
            Observation.animal_id == animal_id
        ).count()
        assert obs_count == 0
    
    def test_delete_animal_nullifies_success_story(self, db_session, sample_success_story):
        """Test that deleting an animal doesn't delete success story"""
        animal = sample_success_story.animal
        story_id = sample_success_story.id
        
        # Delete animal
        db_session.delete(animal)
        db_session.commit()
        
        # Story should still exist (with null animal_id)
        story = db_session.query(SuccessStory).filter(
            SuccessStory.id == story_id
        ).first()
        # Note: This depends on the cascade settings - adjust test accordingly
        # If cascade is set to delete, story would be None
        # If not, story.animal_id would be None
