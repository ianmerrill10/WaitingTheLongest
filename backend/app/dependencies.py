"""
Waiting The Longest™ - Dependency Injection
============================================
Dependency management for FastAPI.
"""

from typing import Optional, Generator
from functools import lru_cache

from sqlalchemy.orm import Session
from fastapi import Depends


# =============================================================================
# Database Dependencies
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.
    
    Yields a database session and ensures it's closed after use.
    """
    from .database import SessionLocal
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Configuration Dependencies
# =============================================================================

@lru_cache()
def get_settings():
    """
    Get application settings (cached).
    
    Uses lru_cache for performance - settings are loaded once.
    """
    from .config import Settings
    return Settings()


# =============================================================================
# Service Dependencies
# =============================================================================

def get_feature_flags():
    """Get the feature flag manager."""
    from .feature_flags import get_feature_flags as _get_feature_flags
    return _get_feature_flags()


def get_cache():
    """Get the cache instance."""
    from .cache import cache
    return cache


# =============================================================================
# Request Context Dependencies
# =============================================================================

from fastapi import Request
import uuid


def get_request_id(request: Request) -> str:
    """
    Get or generate a request ID.
    
    Checks for existing X-Request-ID header, otherwise generates one.
    """
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())[:8]
    
    # Store in request state for later use
    request.state.request_id = request_id
    return request_id


def get_client_ip(request: Request) -> str:
    """Get the client IP address."""
    # Check forwarded headers
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Get the user agent string."""
    return request.headers.get("User-Agent", "unknown")


# =============================================================================
# Optional User Dependencies
# =============================================================================

async def get_current_user_optional(request: Request) -> Optional[str]:
    """
    Get the current user if authenticated (optional).
    
    Returns None if not authenticated.
    For a real auth system, this would validate tokens.
    """
    # Check for user ID in various places
    user_id = request.headers.get("X-User-ID")
    
    if not user_id:
        # Check cookies
        user_id = request.cookies.get("user_id")
    
    return user_id


# =============================================================================
# Common Dependencies
# =============================================================================

class CommonDependencies:
    """
    Common dependencies bundled together.
    
    Usage:
        @app.get("/items")
        async def get_items(commons: CommonDependencies = Depends()):
            db = commons.db
            settings = commons.settings
    """
    
    def __init__(
        self,
        db: Session = Depends(get_db),
        settings = Depends(get_settings),
        request_id: str = Depends(get_request_id),
    ):
        self.db = db
        self.settings = settings
        self.request_id = request_id


# =============================================================================
# Pagination Dependencies
# =============================================================================

from dataclasses import dataclass


@dataclass
class PaginationParams:
    """Pagination parameters."""
    page: int
    page_size: int
    offset: int
    
    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> PaginationParams:
    """
    Get pagination parameters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        max_page_size: Maximum allowed page size
    
    Returns:
        PaginationParams with validated values
    """
    # Validate and clamp values
    page = max(1, page)
    page_size = max(1, min(page_size, max_page_size))
    offset = (page - 1) * page_size
    
    return PaginationParams(
        page=page,
        page_size=page_size,
        offset=offset,
    )


# =============================================================================
# Filter Dependencies
# =============================================================================

from typing import List


@dataclass
class AnimalFilters:
    """Filter parameters for animal queries."""
    species: Optional[str] = None
    breed: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    state: Optional[str] = None
    shelter_id: Optional[int] = None
    min_days_waiting: Optional[int] = None
    search: Optional[str] = None


def get_animal_filters(
    species: Optional[str] = None,
    breed: Optional[str] = None,
    age: Optional[str] = None,
    gender: Optional[str] = None,
    state: Optional[str] = None,
    shelter_id: Optional[int] = None,
    min_days_waiting: Optional[int] = None,
    search: Optional[str] = None,
) -> AnimalFilters:
    """Get filter parameters for animal queries."""
    return AnimalFilters(
        species=species,
        breed=breed,
        age=age,
        gender=gender,
        state=state,
        shelter_id=shelter_id,
        min_days_waiting=min_days_waiting,
        search=search,
    )
