"""
===============================================================================
Waiting The Longest™ - Database Models
===============================================================================
Purpose: SQLAlchemy ORM models for the pet adoption platform. Defines the
         database schema for all entities including animals, observations,
         shelters, success stories, and monetization tracking.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: sqlalchemy
Related Files: database.py, schemas.py, crud.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Core Models:
- Animal: Canonical animal records (deduplicated)
- Observation: Raw sightings from data sources
- Shelter: Shelter/rescue organization information
- SuccessStory: Adoption success stories for social content
- SocialPromotion: Social media post tracking
- AffiliateClick: Revenue tracking for affiliate links
===============================================================================
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Float, Text,
    Index, ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
import enum

from .database import Base


# =============================================================================
# Enums
# =============================================================================

class AnimalStatus(str, enum.Enum):
    """Status of an animal in the system"""
    AVAILABLE = "available"
    ADOPTED = "adopted"
    PENDING = "pending"
    TRANSFERRED = "transferred"
    DECEASED = "deceased"
    UNKNOWN = "unknown"


class Species(str, enum.Enum):
    """Supported animal species"""
    DOG = "dog"
    CAT = "cat"
    OTHER = "other"


class SocialPlatform(str, enum.Enum):
    """Social media platforms for promotion"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    YOUTUBE = "youtube"


class PromotionStatus(str, enum.Enum):
    """Status of a social media promotion"""
    PENDING = "pending"
    GENERATING = "generating"
    UPLOADING = "uploading"
    POSTED = "posted"
    FAILED = "failed"


# =============================================================================
# Core Models
# =============================================================================

class Animal(Base):
    """
    Canonical animal record - deduplicated across all sources.

    This is the heart of Waiting The Longest™. Each record represents
    a unique animal, with their first_seen_at date tracking how long
    they've been waiting for adoption.
    """
    __tablename__ = "animals"

    id = Column(Integer, primary_key=True, index=True)

    # Core identification
    species = Column(String(20), index=True, default="dog")
    canonical_name = Column(String(200), index=True, nullable=True)

    # Timing - THE KEY TO OUR MISSION!
    first_seen_at = Column(DateTime, index=True, default=datetime.utcnow)
    last_seen_at = Column(DateTime, index=True, default=datetime.utcnow)

    # Status tracking
    status = Column(String(20), index=True, default="available")
    transfer_count = Column(Integer, default=0)

    # Physical attributes (for matching/display)
    breed_primary = Column(String(100), nullable=True)
    breed_secondary = Column(String(100), nullable=True)
    color_primary = Column(String(50), nullable=True)
    age_group = Column(String(20), nullable=True)  # puppy, adult, senior
    size = Column(String(20), nullable=True)  # small, medium, large
    gender = Column(String(10), nullable=True)

    # Perceptual hash for image deduplication
    photo_phash = Column(String(64), index=True, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    observations = relationship("Observation", back_populates="animal", cascade="all, delete-orphan")
    success_stories = relationship("SuccessStory", back_populates="animal")
    promotions = relationship("SocialPromotion", back_populates="animal")

    # Indexes for performance
    __table_args__ = (
        Index('idx_animal_species_status', 'species', 'status'),
        Index('idx_animal_first_seen', 'first_seen_at'),
        Index('idx_animal_phash', 'photo_phash'),
    )

    @property
    def days_waiting(self) -> int:
        """Calculate days this animal has been waiting"""
        if self.first_seen_at:
            return (datetime.now(timezone.utc).replace(tzinfo=None) - self.first_seen_at).days
        return 0


class Observation(Base):
    """
    Raw observation/sighting of an animal from a data source.

    Multiple observations can link to a single Animal record
    (after deduplication). This tracks the animal across different
    shelters and sources.
    """
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), index=True)

    # Source tracking
    source = Column(String(50), index=True)  # rescuegroups, adoptapet, manual
    external_id = Column(String(100), index=True)

    # Shelter info
    shelter_id = Column(Integer, ForeignKey("shelters.id"), nullable=True)
    shelter_name = Column(String(200))

    # Animal details at time of observation
    name = Column(String(200))
    breed_primary = Column(String(100), nullable=True)
    breed_secondary = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    # Photos
    photo_url = Column(Text, nullable=True)
    photo_gallery_json = Column(JSON, nullable=True)

    # Location
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)

    # External links
    listing_url = Column(Text, nullable=True)

    # Timing
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    animal = relationship("Animal", back_populates="observations")
    shelter = relationship("Shelter", back_populates="observations")

    __table_args__ = (
        Index('idx_obs_source_external', 'source', 'external_id'),
    )


class Shelter(Base):
    """
    Shelter/rescue organization information.
    """
    __tablename__ = "shelters"

    id = Column(Integer, primary_key=True, index=True)

    # Identification
    name = Column(String(200), index=True)
    source = Column(String(50))  # Where we got this shelter info
    external_id = Column(String(100), index=True, nullable=True)

    # Contact info
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    website = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    last_verified_at = Column(DateTime, default=datetime.utcnow)

    # Location
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Stats
    total_animals = Column(Integer, default=0)

    # Social media (for rescue/shelter registry)
    facebook_url = Column(Text, nullable=True)
    instagram_url = Column(Text, nullable=True)
    twitter_url = Column(Text, nullable=True)
    tiktok_url = Column(Text, nullable=True)

    # Organization type (shelter, rescue, sanctuary, municipal, etc.)
    org_type = Column(String(50), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    observations = relationship("Observation", back_populates="shelter")


class SuccessStory(Base):
    """
    Adoption success stories - crucial for social media content!

    These stories power our TikTok videos and inspire potential adopters.
    "After 500 days, Max finally found his forever home!"
    """
    __tablename__ = "success_stories"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=True)

    # Story content
    pet_name = Column(String(200))
    adopter_name = Column(String(200), nullable=True)  # Optional
    story_text = Column(Text)

    # Key metric for our content
    days_waited = Column(Integer, default=0)

    # Media
    photo_urls = Column(JSON, nullable=True)  # Array of photo URLs
    video_url = Column(Text, nullable=True)

    # Dates
    adoption_date = Column(DateTime, nullable=True)
    submission_date = Column(DateTime, default=datetime.utcnow)

    # Moderation
    is_approved = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)

    # Contact (for follow-up, not displayed)
    contact_email = Column(String(200), nullable=True)

    # Relationship
    animal = relationship("Animal", back_populates="success_stories")

    __table_args__ = (
        Index('idx_story_approved', 'is_approved'),
        Index('idx_story_featured', 'is_featured'),
    )


class SocialPromotion(Base):
    """
    Track social media promotions for animals.

    Helps us know which animals we've promoted and on which platforms.
    """
    __tablename__ = "social_promotions"

    id = Column(Integer, primary_key=True, index=True)
    animal_id = Column(Integer, ForeignKey("animals.id"))

    # Platform info
    platform = Column(String(20), index=True)  # tiktok, instagram, etc.
    status = Column(String(20), default="pending")  # pending, posted, failed

    # Content
    video_path = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)

    # External references
    post_url = Column(Text, nullable=True)
    post_id = Column(String(100), nullable=True)

    # Engagement metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)

    # Timing
    scheduled_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    animal = relationship("Animal", back_populates="promotions")

    __table_args__ = (
        Index('idx_promo_platform_status', 'platform', 'status'),
    )


# =============================================================================
# Affiliate/Monetization Models
# =============================================================================

class AffiliateClick(Base):
    """
    Track affiliate link clicks for revenue attribution.
    """
    __tablename__ = "affiliate_clicks"

    id = Column(Integer, primary_key=True, index=True)

    # Click info
    product_id = Column(String(100), index=True)
    affiliate_program = Column(String(50))  # amazon, chewy, etc.

    # Context
    source_page = Column(String(200), nullable=True)  # Which page had the link
    animal_id = Column(Integer, ForeignKey("animals.id"), nullable=True)

    # Tracking
    session_id = Column(String(100), nullable=True)
    ip_hash = Column(String(64), nullable=True)  # Hashed for privacy
    user_agent = Column(Text, nullable=True)

    # Conversion tracking
    converted = Column(Boolean, default=False)
    conversion_value = Column(Float, nullable=True)

    # Timestamp
    clicked_at = Column(DateTime, default=datetime.utcnow)


class ContactSubmission(Base):
    """
    Contact form submissions from users.
    
    Stores inquiries, feedback, and partnership requests.
    """
    __tablename__ = "contact_submissions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Contact info
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)
    subject = Column(String(300), nullable=False)
    message = Column(Text, nullable=False)
    
    # Metadata
    ip_hash = Column(String(64), nullable=True)  # Hashed for privacy
    user_agent = Column(Text, nullable=True)
    
    # Status tracking
    is_read = Column(Boolean, default=False)
    is_responded = Column(Boolean, default=False)
    responded_at = Column(DateTime, nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_contact_email', 'email'),
        Index('idx_contact_submitted', 'submitted_at'),
    )


# =============================================================================
# Knowledge Library Models
# =============================================================================

class Article(Base):
    """
    Knowledge Library Article.
    """
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(200), unique=True, index=True)
    title = Column(String(200), nullable=False)
    category = Column(String(100), index=True, nullable=False)
    content = Column(Text, nullable=False)
    read_time = Column(String(50), default="5 min read")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = Column(Boolean, default=True)
    views = Column(Integer, default=0)

