"""
Waiting The Longest™ - Type Definitions
=========================================
Type aliases and shared type definitions.
"""

from typing import TypeAlias, TypeVar, Generic, Any
from datetime import datetime, date
from dataclasses import dataclass
from enum import Enum


# =============================================================================
# Basic Type Aliases
# =============================================================================

# IDs
AnimalID: TypeAlias = int
ShelterID: TypeAlias = int
UserID: TypeAlias = str
JobID: TypeAlias = str
RequestID: TypeAlias = str

# External IDs
ExternalID: TypeAlias = str
RescueGroupsID: TypeAlias = str
PetfinderID: TypeAlias = str

# Values
Email: TypeAlias = str
URL: TypeAlias = str
PhoneNumber: TypeAlias = str
ZipCode: TypeAlias = str

# Time
Timestamp: TypeAlias = datetime
DateOnly: TypeAlias = date
DaysWaiting: TypeAlias = int

# JSON-like structures
JSONDict: TypeAlias = dict[str, Any]
JSONList: TypeAlias = list[Any]
JSONValue: TypeAlias = str | int | float | bool | None | JSONDict | JSONList


# =============================================================================
# Generic Types
# =============================================================================

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


@dataclass
class Result(Generic[T]):
    """Generic result wrapper for operations that can fail."""
    
    success: bool
    data: T | None = None
    error: str | None = None
    
    @classmethod
    def ok(cls, data: T) -> "Result[T]":
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str) -> "Result[T]":
        return cls(success=False, error=error)
    
    def unwrap(self) -> T:
        """Get the data or raise an exception."""
        if not self.success:
            raise ValueError(self.error)
        return self.data
    
    def unwrap_or(self, default: T) -> T:
        """Get the data or return a default."""
        return self.data if self.success else default


@dataclass
class Page(Generic[T]):
    """Generic paginated result."""
    
    items: list[T]
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1


# =============================================================================
# Domain Enums
# =============================================================================

class Species(str, Enum):
    """Animal species."""
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    BIRD = "bird"
    SMALL_ANIMAL = "small_animal"
    REPTILE = "reptile"
    FARM_ANIMAL = "farm_animal"
    OTHER = "other"


class AnimalAge(str, Enum):
    """Animal age categories."""
    BABY = "baby"
    YOUNG = "young"
    ADULT = "adult"
    SENIOR = "senior"


class AnimalSize(str, Enum):
    """Animal size categories."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra_large"


class AnimalGender(str, Enum):
    """Animal gender."""
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class AdoptionStatus(str, Enum):
    """Adoption status."""
    AVAILABLE = "available"
    PENDING = "pending"
    ADOPTED = "adopted"
    ON_HOLD = "on_hold"


class SortField(str, Enum):
    """Fields for sorting animals."""
    DAYS_WAITING = "days_waiting"
    NAME = "name"
    INTAKE_DATE = "intake_date"
    UPDATED_AT = "updated_at"
    SPECIES = "species"


class SortOrder(str, Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# API Types
# =============================================================================

@dataclass
class APIError:
    """Standard API error response."""
    
    code: str
    message: str
    details: dict | None = None
    
    def to_dict(self) -> dict:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


@dataclass
class APIResponse(Generic[T]):
    """Standard API response wrapper."""
    
    data: T
    meta: dict | None = None
    
    def to_dict(self) -> dict:
        result = {"data": self.data}
        if self.meta:
            result["meta"] = self.meta
        return result


# =============================================================================
# Event Types
# =============================================================================

@dataclass
class DomainEvent:
    """Base class for domain events."""
    
    event_type: str
    occurred_at: datetime
    data: dict
    
    @classmethod
    def create(cls, event_type: str, **data) -> "DomainEvent":
        return cls(
            event_type=event_type,
            occurred_at=datetime.utcnow(),
            data=data,
        )


@dataclass
class AnimalCreatedEvent(DomainEvent):
    """Event when an animal is added."""
    
    @classmethod
    def create(cls, animal_id: int, **data) -> "AnimalCreatedEvent":
        return cls(
            event_type="animal.created",
            occurred_at=datetime.utcnow(),
            data={"animal_id": animal_id, **data},
        )


@dataclass
class AnimalAdoptedEvent(DomainEvent):
    """Event when an animal is adopted."""
    
    @classmethod
    def create(cls, animal_id: int, days_waiting: int, **data) -> "AnimalAdoptedEvent":
        return cls(
            event_type="animal.adopted",
            occurred_at=datetime.utcnow(),
            data={"animal_id": animal_id, "days_waiting": days_waiting, **data},
        )


# =============================================================================
# Configuration Types
# =============================================================================

@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    url: str
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class CacheConfig:
    """Cache configuration."""
    
    enabled: bool = True
    backend: str = "memory"  # memory, redis
    ttl: int = 300  # seconds
    redis_url: str | None = None


@dataclass
class APIConfig:
    """API configuration."""
    
    title: str = "Waiting The Longest API"
    version: str = "1.0.0"
    rate_limit: int = 100  # requests per minute
    cors_origins: list[str] | None = None


# =============================================================================
# Callable Types
# =============================================================================

from typing import Callable, Awaitable

# Function types
SyncHandler = Callable[..., Any]
AsyncHandler = Callable[..., Awaitable[Any]]
Handler = SyncHandler | AsyncHandler

# Middleware types
Middleware = Callable[[Handler], Handler]

# Event handlers
EventHandler = Callable[[DomainEvent], Awaitable[None]]


# =============================================================================
# Utility Functions
# =============================================================================

def is_valid_species(value: str) -> bool:
    """Check if a string is a valid species."""
    try:
        Species(value.lower())
        return True
    except ValueError:
        return False


def normalize_species(value: str) -> Species:
    """Normalize a species string to enum."""
    value = value.lower().strip()
    
    # Common mappings
    mappings = {
        "dogs": Species.DOG,
        "cats": Species.CAT,
        "rabbits": Species.RABBIT,
        "birds": Species.BIRD,
        "guinea pig": Species.SMALL_ANIMAL,
        "hamster": Species.SMALL_ANIMAL,
        "ferret": Species.SMALL_ANIMAL,
    }
    
    if value in mappings:
        return mappings[value]
    
    try:
        return Species(value)
    except ValueError:
        return Species.OTHER
