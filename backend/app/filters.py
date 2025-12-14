"""
Waiting The Longest™ - Filter Utilities
=========================================
Reusable filtering for animal queries.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime, timedelta
from enum import Enum


# =============================================================================
# Filter Enums
# =============================================================================

class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    """Available sort fields for animals."""
    DAYS_WAITING = "days_waiting"
    NAME = "name"
    INTAKE_DATE = "intake_date"
    SPECIES = "species"
    AGE = "age"
    UPDATED_AT = "updated_at"


class Species(str, Enum):
    """Supported species types."""
    DOG = "dog"
    CAT = "cat"
    RABBIT = "rabbit"
    BIRD = "bird"
    SMALL_ANIMAL = "small animal"
    HORSE = "horse"
    REPTILE = "reptile"
    OTHER = "other"


class Age(str, Enum):
    """Age categories."""
    BABY = "baby"
    YOUNG = "young"
    ADULT = "adult"
    SENIOR = "senior"


class Gender(str, Enum):
    """Gender options."""
    MALE = "male"
    FEMALE = "female"


class Size(str, Enum):
    """Size categories."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    EXTRA_LARGE = "extra large"


# =============================================================================
# Filter Parameters
# =============================================================================

@dataclass
class AnimalFilters:
    """Filter parameters for animal queries."""
    
    # Basic filters
    species: str | None = None
    breed: str | None = None
    age: str | None = None
    gender: str | None = None
    size: str | None = None
    
    # Location filters
    state: str | None = None
    city: str | None = None
    zip_code: str | None = None
    distance_miles: int | None = None
    
    # Shelter filter
    shelter_id: int | None = None
    shelter_name: str | None = None
    
    # Time-based filters
    min_days_waiting: int | None = None
    max_days_waiting: int | None = None
    intake_after: datetime | None = None
    intake_before: datetime | None = None
    
    # Status filters
    is_adopted: bool = False
    is_featured: bool | None = None
    has_photos: bool | None = None
    
    # Attributes filters
    good_with_kids: bool | None = None
    good_with_dogs: bool | None = None
    good_with_cats: bool | None = None
    house_trained: bool | None = None
    special_needs: bool | None = None
    
    # Search
    search_query: str | None = None
    
    # Sorting
    sort_by: str = "days_waiting"
    sort_order: str = "desc"
    
    # Tags
    tags: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert filters to dictionary."""
        return {
            k: v for k, v in {
                "species": self.species,
                "breed": self.breed,
                "age": self.age,
                "gender": self.gender,
                "size": self.size,
                "state": self.state,
                "city": self.city,
                "zip_code": self.zip_code,
                "shelter_id": self.shelter_id,
                "min_days_waiting": self.min_days_waiting,
                "max_days_waiting": self.max_days_waiting,
                "is_adopted": self.is_adopted,
                "search_query": self.search_query,
                "sort_by": self.sort_by,
                "sort_order": self.sort_order,
            }.items() if v is not None
        }
    
    def is_empty(self) -> bool:
        """Check if no filters are applied."""
        return all([
            self.species is None,
            self.breed is None,
            self.age is None,
            self.gender is None,
            self.size is None,
            self.state is None,
            self.city is None,
            self.shelter_id is None,
            self.search_query is None,
            len(self.tags) == 0,
        ])
    
    @classmethod
    def from_request(cls, **kwargs) -> "AnimalFilters":
        """Create filters from request parameters."""
        filters = cls()
        
        # Map request params to filter fields
        if species := kwargs.get("species"):
            filters.species = species.lower()
        if breed := kwargs.get("breed"):
            filters.breed = breed
        if age := kwargs.get("age"):
            filters.age = age.lower()
        if gender := kwargs.get("gender"):
            filters.gender = gender.lower()
        if size := kwargs.get("size"):
            filters.size = size.lower()
        if state := kwargs.get("state"):
            filters.state = state.upper()
        if city := kwargs.get("city"):
            filters.city = city
        if shelter_id := kwargs.get("shelter_id"):
            filters.shelter_id = int(shelter_id)
        if min_days := kwargs.get("min_days_waiting"):
            filters.min_days_waiting = int(min_days)
        if max_days := kwargs.get("max_days_waiting"):
            filters.max_days_waiting = int(max_days)
        if search := kwargs.get("q", kwargs.get("search")):
            filters.search_query = search
        if sort := kwargs.get("sort", kwargs.get("sort_by")):
            filters.sort_by = sort
        if order := kwargs.get("order", kwargs.get("sort_order")):
            filters.sort_order = order.lower()
        
        return filters


# =============================================================================
# Filter Builder
# =============================================================================

class FilterBuilder:
    """
    Build SQLAlchemy filters from AnimalFilters.
    """
    
    def __init__(self, model: Any):
        """
        Initialize with the model to filter.
        
        Args:
            model: SQLAlchemy model class (e.g., Animal)
        """
        self.model = model
        self.conditions: list[Any] = []
    
    def apply_filters(self, filters: AnimalFilters) -> list[Any]:
        """
        Apply all filters and return SQLAlchemy conditions.
        """
        self.conditions = []
        
        # Species filter
        if filters.species:
            self.conditions.append(
                self.model.species.ilike(filters.species)
            )
        
        # Breed filter (partial match)
        if filters.breed:
            self.conditions.append(
                self.model.breed.ilike(f"%{filters.breed}%")
            )
        
        # Age filter
        if filters.age:
            self.conditions.append(
                self.model.age.ilike(filters.age)
            )
        
        # Gender filter
        if filters.gender:
            self.conditions.append(
                self.model.gender.ilike(filters.gender)
            )
        
        # Size filter
        if filters.size:
            self.conditions.append(
                self.model.size.ilike(filters.size)
            )
        
        # State filter (through shelter)
        if filters.state:
            # This requires a join with shelters
            pass
        
        # Shelter ID filter
        if filters.shelter_id:
            self.conditions.append(
                self.model.shelter_id == filters.shelter_id
            )
        
        # Adoption status
        self.conditions.append(
            self.model.is_adopted == filters.is_adopted
        )
        
        # Days waiting filters
        if filters.min_days_waiting is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=filters.min_days_waiting)
            self.conditions.append(
                self.model.intake_date <= cutoff_date
            )
        
        if filters.max_days_waiting is not None:
            cutoff_date = datetime.utcnow() - timedelta(days=filters.max_days_waiting)
            self.conditions.append(
                self.model.intake_date >= cutoff_date
            )
        
        # Date range filters
        if filters.intake_after:
            self.conditions.append(
                self.model.intake_date >= filters.intake_after
            )
        
        if filters.intake_before:
            self.conditions.append(
                self.model.intake_date <= filters.intake_before
            )
        
        # Search query (basic implementation)
        if filters.search_query:
            search_term = f"%{filters.search_query}%"
            from sqlalchemy import or_
            self.conditions.append(
                or_(
                    self.model.name.ilike(search_term),
                    self.model.breed.ilike(search_term),
                    self.model.description.ilike(search_term),
                )
            )
        
        return self.conditions
    
    def get_sort_column(self, filters: AnimalFilters) -> Any:
        """Get the column to sort by."""
        sort_columns = {
            "days_waiting": self.model.intake_date,
            "intake_date": self.model.intake_date,
            "name": self.model.name,
            "species": self.model.species,
            "age": self.model.age,
            "updated_at": self.model.updated_at if hasattr(self.model, "updated_at") else self.model.intake_date,
        }
        
        column = sort_columns.get(filters.sort_by, self.model.intake_date)
        
        # For days_waiting, we sort by intake_date (earlier = more days)
        if filters.sort_by == "days_waiting":
            # Descending days_waiting = ascending intake_date
            if filters.sort_order == "desc":
                return column.asc()
            return column.desc()
        
        if filters.sort_order == "desc":
            return column.desc()
        return column.asc()


# =============================================================================
# Filter Options (for dropdowns)
# =============================================================================

@dataclass
class FilterOption:
    """Single filter option for dropdowns."""
    value: str
    label: str
    count: int = 0


@dataclass
class FilterOptions:
    """Available filter options with counts."""
    
    species: list[FilterOption] = field(default_factory=list)
    breeds: list[FilterOption] = field(default_factory=list)
    ages: list[FilterOption] = field(default_factory=list)
    genders: list[FilterOption] = field(default_factory=list)
    sizes: list[FilterOption] = field(default_factory=list)
    states: list[FilterOption] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "species": [{"value": o.value, "label": o.label, "count": o.count} for o in self.species],
            "breeds": [{"value": o.value, "label": o.label, "count": o.count} for o in self.breeds],
            "ages": [{"value": o.value, "label": o.label, "count": o.count} for o in self.ages],
            "genders": [{"value": o.value, "label": o.label, "count": o.count} for o in self.genders],
            "sizes": [{"value": o.value, "label": o.label, "count": o.count} for o in self.sizes],
            "states": [{"value": o.value, "label": o.label, "count": o.count} for o in self.states],
        }


def get_default_species_options() -> list[FilterOption]:
    """Get default species filter options."""
    return [
        FilterOption("dog", "Dogs"),
        FilterOption("cat", "Cats"),
        FilterOption("rabbit", "Rabbits"),
        FilterOption("bird", "Birds"),
        FilterOption("small animal", "Small Animals"),
        FilterOption("horse", "Horses"),
        FilterOption("reptile", "Reptiles"),
        FilterOption("other", "Other"),
    ]


def get_default_age_options() -> list[FilterOption]:
    """Get default age filter options."""
    return [
        FilterOption("baby", "Baby"),
        FilterOption("young", "Young"),
        FilterOption("adult", "Adult"),
        FilterOption("senior", "Senior"),
    ]


def get_default_gender_options() -> list[FilterOption]:
    """Get default gender filter options."""
    return [
        FilterOption("male", "Male"),
        FilterOption("female", "Female"),
    ]


def get_default_size_options() -> list[FilterOption]:
    """Get default size filter options."""
    return [
        FilterOption("small", "Small"),
        FilterOption("medium", "Medium"),
        FilterOption("large", "Large"),
        FilterOption("extra large", "Extra Large"),
    ]
