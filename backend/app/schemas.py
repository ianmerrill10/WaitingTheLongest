"""
===============================================================================
Waiting The Longest™ - Pydantic Schemas
===============================================================================
Purpose: Request/response schemas for API validation and serialization.
         Defines data transfer objects for all API endpoints.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: pydantic
Related Files: main.py, crud.py, models.py

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md
===============================================================================
"""

from pydantic import BaseModel, Field, HttpUrl, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# =============================================================================
# Base Schemas
# =============================================================================

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    class Config:
        from_attributes = True  # Enable ORM mode


# =============================================================================
# Health/Info Schemas
# =============================================================================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    timestamp: str
    version: str


# =============================================================================
# Animal Schemas
# =============================================================================

class AnimalBase(BaseModel):
    """Base animal fields"""
    species: str = "dog"
    canonical_name: Optional[str] = None
    breed_primary: Optional[str] = None
    breed_secondary: Optional[str] = None
    color_primary: Optional[str] = None
    age_group: Optional[str] = None
    size: Optional[str] = None
    gender: Optional[str] = None


class AnimalListItem(BaseSchema):
    """Animal item for list view"""
    id: int
    species: str
    canonical_name: Optional[str]
    breed_primary: Optional[str]
    age_group: Optional[str]
    size: Optional[str]
    gender: Optional[str]
    status: str
    days_waiting: int = Field(..., description="Number of days this animal has been waiting")
    first_seen_at: datetime
    photo_url: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None


class ObservationOut(BaseSchema):
    """Observation output for detail view"""
    id: int
    source: str
    shelter_name: str
    name: str
    description: Optional[str]
    photo_url: Optional[str]
    photo_gallery: List[str] = []
    city: Optional[str]
    state: Optional[str]
    listing_url: Optional[str]
    first_seen_at: datetime
    last_seen_at: datetime


class AnimalDetailResponse(BaseSchema):
    """Detailed animal response"""
    id: int
    species: str
    canonical_name: Optional[str]
    breed_primary: Optional[str]
    breed_secondary: Optional[str]
    color_primary: Optional[str]
    age_group: Optional[str]
    size: Optional[str]
    gender: Optional[str]
    status: str
    transfer_count: int
    days_waiting: int
    first_seen_at: datetime
    last_seen_at: datetime
    observations: List[ObservationOut] = []
    photos: List[str] = []
    description: Optional[str] = None
    adoption_url: Optional[str] = None
    shelter_info: Optional[dict] = None


class AnimalListResponse(BaseModel):
    """Paginated animal list response"""
    items: List[AnimalListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


# =============================================================================
# Success Story Schemas
# =============================================================================

class SuccessStoryCreate(BaseModel):
    """Create a success story submission"""
    pet_name: str = Field(..., min_length=1, max_length=200)
    adopter_name: Optional[str] = Field(None, max_length=200)
    story_text: str = Field(..., min_length=50, max_length=5000)
    days_waited: int = Field(0, ge=0)
    adoption_date: Optional[datetime] = None
    photo_urls: Optional[List[str]] = None
    contact_email: Optional[EmailStr] = None
    animal_id: Optional[int] = None


class SuccessStoryResponse(BaseSchema):
    """Success story submission response"""
    success: bool
    message: str
    story_id: int


class SuccessStoryOut(BaseSchema):
    """Success story for display"""
    id: int
    pet_name: str
    adopter_name: Optional[str]
    story_text: str
    days_waited: int
    adoption_date: Optional[datetime]
    photo_urls: Optional[List[str]]
    is_featured: bool


# =============================================================================
# Search/Filter Schemas
# =============================================================================

class AnimalSearchParams(BaseModel):
    """Animal search parameters"""
    species: Optional[str] = None
    breed: Optional[str] = None
    age_group: Optional[str] = None
    size: Optional[str] = None
    gender: Optional[str] = None
    status: str = "available"
    city: Optional[str] = None
    state: Optional[str] = None
    min_days_waiting: Optional[int] = None
    max_days_waiting: Optional[int] = None


# =============================================================================
# Statistics Schemas
# =============================================================================

class PlatformStats(BaseModel):
    """Platform statistics"""
    total_animals: int
    available_animals: int
    average_wait_days: float
    longest_wait_days: int
    success_stories: int
    mission: str = "Because Every Day Matters"
    updated_at: datetime


# =============================================================================
# Affiliate/Monetization Schemas
# =============================================================================

class ProductRecommendation(BaseModel):
    """Product recommendation with affiliate link"""
    product_id: str
    name: str
    category: str
    pet_type: str
    price_range: str
    affiliate_url: str
    image_url: Optional[str] = None
    description: Optional[str] = None


class AffiliateClickCreate(BaseModel):
    """Track an affiliate click"""
    product_id: str
    affiliate_program: str
    source_page: Optional[str] = None
    animal_id: Optional[int] = None


# =============================================================================
# Social Media Schemas
# =============================================================================

class SocialPromotionCreate(BaseModel):
    """Create a social promotion"""
    animal_id: int
    platform: str
    caption: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class SocialPromotionOut(BaseSchema):
    """Social promotion output"""
    id: int
    animal_id: int
    platform: str
    status: str
    post_url: Optional[str]
    views: int
    likes: int
    shares: int
    posted_at: Optional[datetime]
