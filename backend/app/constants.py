"""
Waiting The Longest™ - Constants
=================================
Application-wide constants and magic values.
"""

from typing import Final


# =============================================================================
# Application Info
# =============================================================================

APP_NAME: Final[str] = "Waiting The Longest"
APP_VERSION: Final[str] = "1.0.0"
APP_DESCRIPTION: Final[str] = "Highlighting shelter animals waiting the longest for adoption"
APP_URL: Final[str] = "https://waitingthelongest.com"
APP_EMAIL: Final[str] = "hello@waitingthelongest.com"


# =============================================================================
# API Configuration
# =============================================================================

API_PREFIX: Final[str] = "/api/v1"
API_VERSION: Final[str] = "v1"

# Rate limiting
RATE_LIMIT_REQUESTS: Final[int] = 100
RATE_LIMIT_PERIOD: Final[int] = 60  # seconds

# Pagination
DEFAULT_PAGE_SIZE: Final[int] = 20
MAX_PAGE_SIZE: Final[int] = 100
MIN_PAGE_SIZE: Final[int] = 1


# =============================================================================
# Database
# =============================================================================

# Connection pool
DB_POOL_SIZE: Final[int] = 5
DB_MAX_OVERFLOW: Final[int] = 10
DB_POOL_TIMEOUT: Final[int] = 30
DB_POOL_RECYCLE: Final[int] = 1800  # 30 minutes

# SQLite defaults
SQLITE_DEFAULT_DB: Final[str] = "waitingthelongest.db"


# =============================================================================
# Cache
# =============================================================================

# TTL values in seconds
CACHE_TTL_SHORT: Final[int] = 60         # 1 minute
CACHE_TTL_MEDIUM: Final[int] = 300       # 5 minutes
CACHE_TTL_LONG: Final[int] = 3600        # 1 hour
CACHE_TTL_DAILY: Final[int] = 86400      # 24 hours

# Cache keys
CACHE_KEY_STATS: Final[str] = "stats:global"
CACHE_KEY_ANIMALS: Final[str] = "animals:all"
CACHE_KEY_SHELTERS: Final[str] = "shelters:all"


# =============================================================================
# Species and Categories
# =============================================================================

SPECIES_DOG: Final[str] = "dog"
SPECIES_CAT: Final[str] = "cat"
SPECIES_RABBIT: Final[str] = "rabbit"
SPECIES_BIRD: Final[str] = "bird"
SPECIES_OTHER: Final[str] = "other"

VALID_SPECIES: Final[tuple[str, ...]] = (
    SPECIES_DOG,
    SPECIES_CAT,
    SPECIES_RABBIT,
    SPECIES_BIRD,
    SPECIES_OTHER,
)

# Age categories
AGE_BABY: Final[str] = "baby"
AGE_YOUNG: Final[str] = "young"
AGE_ADULT: Final[str] = "adult"
AGE_SENIOR: Final[str] = "senior"

VALID_AGES: Final[tuple[str, ...]] = (
    AGE_BABY,
    AGE_YOUNG,
    AGE_ADULT,
    AGE_SENIOR,
)

# Size categories
SIZE_SMALL: Final[str] = "small"
SIZE_MEDIUM: Final[str] = "medium"
SIZE_LARGE: Final[str] = "large"
SIZE_XLARGE: Final[str] = "extra_large"

VALID_SIZES: Final[tuple[str, ...]] = (
    SIZE_SMALL,
    SIZE_MEDIUM,
    SIZE_LARGE,
    SIZE_XLARGE,
)

# Gender
GENDER_MALE: Final[str] = "male"
GENDER_FEMALE: Final[str] = "female"
GENDER_UNKNOWN: Final[str] = "unknown"

VALID_GENDERS: Final[tuple[str, ...]] = (
    GENDER_MALE,
    GENDER_FEMALE,
    GENDER_UNKNOWN,
)


# =============================================================================
# Wait Time Milestones
# =============================================================================

MILESTONE_30_DAYS: Final[int] = 30
MILESTONE_60_DAYS: Final[int] = 60
MILESTONE_90_DAYS: Final[int] = 90
MILESTONE_180_DAYS: Final[int] = 180
MILESTONE_365_DAYS: Final[int] = 365

WAIT_THRESHOLDS: Final[dict[str, int]] = {
    "long": 30,
    "very_long": 90,
    "critical": 180,
    "urgent": 365,
}


# =============================================================================
# External Services
# =============================================================================

# RescueGroups
RESCUEGROUPS_API_URL: Final[str] = "https://api.rescuegroups.org/v5"
RESCUEGROUPS_API_VERSION: Final[str] = "v5"

# Petfinder
PETFINDER_API_URL: Final[str] = "https://api.petfinder.com/v2"
PETFINDER_API_VERSION: Final[str] = "v2"

# Adopt-a-Pet
ADOPTAPET_API_URL: Final[str] = "https://api.adoptapet.com"


# =============================================================================
# Image Defaults
# =============================================================================

DEFAULT_ANIMAL_IMAGE: Final[str] = "/images/placeholder-pet.svg"
DEFAULT_SHELTER_IMAGE: Final[str] = "/images/placeholder-shelter.svg"

# Image sizes
IMAGE_SIZE_THUMBNAIL: Final[tuple[int, int]] = (150, 150)
IMAGE_SIZE_SMALL: Final[tuple[int, int]] = (300, 300)
IMAGE_SIZE_MEDIUM: Final[tuple[int, int]] = (600, 600)
IMAGE_SIZE_LARGE: Final[tuple[int, int]] = (1200, 1200)


# =============================================================================
# Validation
# =============================================================================

# String lengths
MAX_NAME_LENGTH: Final[int] = 255
MAX_DESCRIPTION_LENGTH: Final[int] = 5000
MAX_EMAIL_LENGTH: Final[int] = 255
MAX_URL_LENGTH: Final[int] = 2000
MAX_PHONE_LENGTH: Final[int] = 30

# Email regex pattern
EMAIL_PATTERN: Final[str] = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

# URL regex pattern
URL_PATTERN: Final[str] = r"^https?://[^\s/$.?#].[^\s]*$"


# =============================================================================
# HTTP Headers
# =============================================================================

HEADER_REQUEST_ID: Final[str] = "X-Request-ID"
HEADER_RATE_LIMIT: Final[str] = "X-RateLimit-Limit"
HEADER_RATE_REMAINING: Final[str] = "X-RateLimit-Remaining"
HEADER_RATE_RESET: Final[str] = "X-RateLimit-Reset"
HEADER_API_VERSION: Final[str] = "X-API-Version"


# =============================================================================
# Error Codes
# =============================================================================

ERROR_NOT_FOUND: Final[str] = "NOT_FOUND"
ERROR_VALIDATION: Final[str] = "VALIDATION_ERROR"
ERROR_UNAUTHORIZED: Final[str] = "UNAUTHORIZED"
ERROR_FORBIDDEN: Final[str] = "FORBIDDEN"
ERROR_RATE_LIMITED: Final[str] = "RATE_LIMITED"
ERROR_SERVER: Final[str] = "SERVER_ERROR"
ERROR_SERVICE_UNAVAILABLE: Final[str] = "SERVICE_UNAVAILABLE"


# =============================================================================
# Feature Flags (defaults)
# =============================================================================

FEATURE_NEWSLETTER: Final[bool] = True
FEATURE_DONATIONS: Final[bool] = True
FEATURE_SHARING: Final[bool] = True
FEATURE_FAVORITES: Final[bool] = True
FEATURE_DARK_MODE: Final[bool] = True
FEATURE_PWA: Final[bool] = True
FEATURE_ANALYTICS: Final[bool] = True


# =============================================================================
# Social Links
# =============================================================================

SOCIAL_TWITTER: Final[str] = "https://twitter.com/waitingthelongest"
SOCIAL_FACEBOOK: Final[str] = "https://facebook.com/waitingthelongest"
SOCIAL_INSTAGRAM: Final[str] = "https://instagram.com/waitingthelongest"
SOCIAL_GITHUB: Final[str] = "https://github.com/waitingthelongest"


# =============================================================================
# Cookie Names
# =============================================================================

COOKIE_SESSION: Final[str] = "wtl_session"
COOKIE_DARK_MODE: Final[str] = "wtl_dark_mode"
COOKIE_CONSENT: Final[str] = "wtl_cookie_consent"


# =============================================================================
# Environment Names
# =============================================================================

ENV_DEVELOPMENT: Final[str] = "development"
ENV_STAGING: Final[str] = "staging"
ENV_PRODUCTION: Final[str] = "production"
ENV_TESTING: Final[str] = "testing"
