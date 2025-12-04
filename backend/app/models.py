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

    # Location
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Stats
    total_animals = Column(Integer, default=0)

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


# =============================================================================
# Email Marketing Models
# =============================================================================

class EmailStatus(str, enum.Enum):
    """Status of an email in the queue"""
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SequenceType(str, enum.Enum):
    """Types of email sequences"""
    WELCOME = "welcome"
    ABANDONED_CART = "abandoned_cart"
    PRICE_DROP = "price_drop"
    STILL_WAITING = "still_waiting"
    WEEKLY_NEWSLETTER = "weekly_newsletter"
    ADOPTION_FOLLOWUP = "adoption_followup"


class AlertType(str, enum.Enum):
    """Types of price/availability alerts"""
    PRICE_DROP = "price_drop"
    BACK_IN_STOCK = "back_in_stock"
    NEW_ARRIVAL = "new_arrival"
    ANIMAL_AVAILABLE = "animal_available"


class EmailSubscriber(Base):
    """
    Email subscriber for marketing campaigns.

    Tracks newsletter subscriptions, email preferences, and consent.
    GDPR/CAN-SPAM compliant with proper consent tracking.
    """
    __tablename__ = "email_subscribers"

    id = Column(Integer, primary_key=True, index=True)

    # Contact info
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Preferences
    preferred_species = Column(String(20), nullable=True)  # dog, cat, both
    preferred_location = Column(String(100), nullable=True)  # state/region
    preferred_age_group = Column(String(20), nullable=True)  # puppy, adult, senior

    # Subscription status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(100), nullable=True)

    # Consent tracking (GDPR/CAN-SPAM compliance)
    consent_given = Column(Boolean, default=False)
    consent_date = Column(DateTime, nullable=True)
    consent_source = Column(String(100), nullable=True)  # website, popup, footer

    # Communication preferences
    newsletter_enabled = Column(Boolean, default=True)
    product_updates_enabled = Column(Boolean, default=True)
    adoption_alerts_enabled = Column(Boolean, default=True)
    affiliate_emails_enabled = Column(Boolean, default=True)

    # Engagement tracking
    last_email_sent_at = Column(DateTime, nullable=True)
    last_email_opened_at = Column(DateTime, nullable=True)
    last_email_clicked_at = Column(DateTime, nullable=True)
    total_emails_sent = Column(Integer, default=0)
    total_emails_opened = Column(Integer, default=0)
    total_emails_clicked = Column(Integer, default=0)

    # Timestamps
    signup_date = Column(DateTime, default=datetime.utcnow)
    unsubscribe_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    email_sequences = relationship("EmailSequence", back_populates="subscriber", cascade="all, delete-orphan")
    scheduled_emails = relationship("ScheduledEmail", back_populates="subscriber", cascade="all, delete-orphan")
    price_alerts = relationship("PriceAlert", back_populates="subscriber", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_subscriber_email', 'email'),
        Index('idx_subscriber_active', 'is_active'),
        Index('idx_subscriber_verified', 'is_verified'),
    )


class EmailSequence(Base):
    """
    Email sequence/automation tracking.

    Tracks user progress through email sequences like welcome series,
    abandoned cart, or post-adoption follow-ups.
    """
    __tablename__ = "email_sequences"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("email_subscribers.id"), index=True)

    # Sequence info
    sequence_type = Column(String(50), index=True)  # welcome, abandoned_cart, etc.
    current_step = Column(Integer, default=0)  # Current position in sequence
    total_steps = Column(Integer, default=1)  # Total emails in sequence

    # Status
    status = Column(String(20), default="active")  # active, paused, completed, cancelled
    is_completed = Column(Boolean, default=False)

    # Context data (JSON for flexible storage)
    context_data = Column(JSON, nullable=True)  # e.g., {"animal_id": 123}

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    next_email_at = Column(DateTime, nullable=True)
    last_email_sent_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriber = relationship("EmailSubscriber", back_populates="email_sequences")

    __table_args__ = (
        Index('idx_sequence_type_status', 'sequence_type', 'status'),
        Index('idx_sequence_next_email', 'next_email_at'),
    )


class ScheduledEmail(Base):
    """
    Queue of scheduled emails waiting to be sent.

    Provides reliable email delivery with retry logic and tracking.
    """
    __tablename__ = "scheduled_emails"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("email_subscribers.id"), index=True)
    sequence_id = Column(Integer, ForeignKey("email_sequences.id"), nullable=True)

    # Email content
    email_type = Column(String(100), index=True)  # welcome_1, newsletter_weekly, etc.
    subject = Column(String(500), nullable=False)
    template_name = Column(String(100), nullable=True)  # Template file name

    # Template variables (JSON)
    template_data = Column(JSON, nullable=True)

    # Scheduling
    scheduled_at = Column(DateTime, index=True, nullable=False)
    sent_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String(20), default="pending", index=True)  # pending, sending, sent, failed
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Tracking
    external_id = Column(String(100), nullable=True)  # ID from email provider
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subscriber = relationship("EmailSubscriber", back_populates="scheduled_emails")

    __table_args__ = (
        Index('idx_email_status_scheduled', 'status', 'scheduled_at'),
        Index('idx_email_type', 'email_type'),
    )


class PriceAlert(Base):
    """
    Price and availability alerts for products/animals.

    Users can set alerts for price drops on affiliate products or
    when specific animals become available.
    """
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("email_subscribers.id"), index=True)

    # Alert type
    alert_type = Column(String(50), index=True)  # price_drop, animal_available, new_arrival

    # Target info
    target_type = Column(String(50))  # product, animal
    target_id = Column(String(100), index=True)  # Product ASIN or Animal ID
    target_name = Column(String(255), nullable=True)

    # Price tracking (for products)
    original_price = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)  # Alert when price drops to this
    current_price = Column(Float, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    triggered_at = Column(DateTime, nullable=True)

    # Notification
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Auto-expire after X days

    # Relationships
    subscriber = relationship("EmailSubscriber", back_populates="price_alerts")

    __table_args__ = (
        Index('idx_alert_active_type', 'is_active', 'alert_type'),
        Index('idx_alert_target', 'target_type', 'target_id'),
    )
