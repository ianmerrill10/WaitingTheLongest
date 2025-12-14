"""
Waiting The Longest™ - Response Models
========================================
Consistent API response structures.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int = Field(..., description="Current page number", ge=1)
    page_size: int = Field(..., description="Items per page", ge=1)
    total_items: int = Field(..., description="Total number of items", ge=0)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")
    
    @classmethod
    def create(
        cls,
        page: int,
        page_size: int,
        total_items: int,
    ) -> "PaginationMeta":
        """Create pagination metadata."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")
    
    class Config:
        from_attributes = True


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Animal Response Models
# =============================================================================

class AnimalSummary(BaseModel):
    """Brief animal information for lists."""
    id: int
    name: str
    species: str
    breed: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    days_waiting: int = Field(..., description="Days waiting for adoption")
    photo_url: Optional[str] = None
    shelter_name: Optional[str] = None
    state: Optional[str] = None
    
    class Config:
        from_attributes = True


class AnimalDetail(AnimalSummary):
    """Full animal information."""
    description: Optional[str] = None
    shelter_id: Optional[int] = None
    shelter_city: Optional[str] = None
    intake_date: Optional[datetime] = None
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    photos: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


class AnimalStats(BaseModel):
    """Statistics about animals."""
    total_animals: int
    total_dogs: int
    total_cats: int
    total_other: int
    avg_days_waiting: float
    max_days_waiting: int
    animals_adopted_this_month: int


# =============================================================================
# Shelter Response Models
# =============================================================================

class ShelterSummary(BaseModel):
    """Brief shelter information for lists."""
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    animal_count: int = 0
    
    class Config:
        from_attributes = True


class ShelterDetail(ShelterSummary):
    """Full shelter information."""
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    external_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    animals: List[AnimalSummary] = Field(default_factory=list)
    
    class Config:
        from_attributes = True


# =============================================================================
# Filter Options Response
# =============================================================================

class FilterOption(BaseModel):
    """A single filter option."""
    value: str
    label: str
    count: Optional[int] = None


class FilterOptions(BaseModel):
    """Available filter options."""
    species: List[FilterOption] = Field(default_factory=list)
    breeds: List[FilterOption] = Field(default_factory=list)
    ages: List[FilterOption] = Field(default_factory=list)
    genders: List[FilterOption] = Field(default_factory=list)
    states: List[FilterOption] = Field(default_factory=list)


# =============================================================================
# Newsletter Response
# =============================================================================

class NewsletterSubscriptionResponse(BaseModel):
    """Response for newsletter subscription."""
    success: bool
    message: str
    subscriber_id: Optional[str] = None


# =============================================================================
# Health Check Response
# =============================================================================

class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, Any] = Field(default_factory=dict, description="Individual check results")


# =============================================================================
# Analytics Response
# =============================================================================

class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_animals: int
    animals_by_species: Dict[str, int]
    avg_days_waiting: float
    longest_waiting: List[AnimalSummary]
    total_shelters: int
    recent_adoptions: int
