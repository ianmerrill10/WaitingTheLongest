"""
===============================================================================
Waiting The Longest™ - Configuration Settings
===============================================================================
Purpose: Centralized configuration management using Pydantic Settings for 
         environment variable loading and validation.

Author: Waiting The Longest™ Development Team
Last Updated: 2025-01-15
Dependencies: pydantic_settings, os
Related Files: .env, .env.example

IMPORTANT: Any changes to this file MUST be documented in OWNERS_MANUAL.md

Application configuration using Pydantic Settings for environment variable
management and validation.
===============================================================================
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ==========================================================================
    # Application Settings
    # ==========================================================================
    APP_NAME: str = "Waiting The Longest™"
    APP_TAGLINE: str = "Because Every Day Matters"
    DEBUG: bool = False
    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING"

    # ==========================================================================
    # Database Configuration
    # ==========================================================================
    DATABASE_URL: str = "postgresql://waiting_user:CHANGE_PASSWORD@localhost:5432/waiting_the_longest"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # ==========================================================================
    # Redis Configuration
    # ==========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None

    # ==========================================================================
    # API Keys (Data Sources)
    # ==========================================================================
    # RescueGroups.org (Primary data source - Petfinder has no API!)
    RESCUEGROUPS_API_KEY: Optional[str] = None

    # Adopt-a-Pet (Secondary)
    ADOPTAPET_API_KEY: Optional[str] = None

    # ==========================================================================
    # Amazon Associates (Monetization)
    # ==========================================================================
    AMAZON_ASSOCIATE_ID: str = "waitingthelon-20"
    AMAZON_ACCESS_KEY: Optional[str] = None
    AMAZON_SECRET_KEY: Optional[str] = None

    # ==========================================================================
    # Social Media APIs
    # ==========================================================================
    TIKTOK_ACCESS_TOKEN: Optional[str] = None
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_PAGE_TOKEN: Optional[str] = None

    # Ayrshare (unified social posting)
    AYRSHARE_API_KEY: Optional[str] = None

    # ==========================================================================
    # CORS & Security
    # ==========================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://waitingthelongest.com",
        "https://www.waitingthelongest.com",
        "https://waitedthelongest.com",
        "https://www.waitedthelongest.com",
    ]

    # JWT Settings
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ==========================================================================
    # File Storage Paths
    # ==========================================================================
    VIDEO_OUTPUT_DIR: str = "/opt/waitingthelongest/data/videos"
    IMAGE_CACHE_DIR: str = "/opt/waitingthelongest/data/images"
    UPLOAD_DIR: str = "/opt/waitingthelongest/data/uploads"

    # ==========================================================================
    # Ingestion Settings
    # ==========================================================================
    INGEST_ENABLED: bool = True
    INGEST_PAGE_LIMIT: int = 50
    INGEST_INTERVAL_HOURS: int = 6

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ==========================================================================
    # Email Marketing Configuration
    # ==========================================================================
    # Email service provider (sendgrid, mailgun, ses)
    EMAIL_PROVIDER: str = "sendgrid"
    EMAIL_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "hello@waitingthelongest.com"
    EMAIL_FROM_NAME: str = "Waiting The Longest™"

    # Physical mailing address (CAN-SPAM compliance)
    EMAIL_MAILING_ADDRESS: str = "Waiting The Longest, 123 Pet Lane, Austin, TX 78701"

    # Email tracking
    EMAIL_TRACKING_ENABLED: bool = True
    EMAIL_OPEN_TRACKING: bool = True
    EMAIL_CLICK_TRACKING: bool = True

    # Newsletter settings
    NEWSLETTER_DAY: str = "sunday"
    NEWSLETTER_TIME: str = "10:00"

    # Email sequence timing (in days/hours)
    WELCOME_SEQUENCE_DAYS: List[int] = [0, 1, 3, 7, 14]
    ABANDONED_CART_HOURS: List[int] = [1, 3, 7]
    STILL_WAITING_REMINDER_DAYS: List[int] = [3, 7, 14]

    # Email retry configuration
    EMAIL_RETRY_BASE_DELAY_MINUTES: int = 5  # Base delay for exponential backoff

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Create global settings instance
settings = Settings()


# ==========================================================================
# Computed Properties
# ==========================================================================

def get_jwt_secret() -> str:
    """Get JWT secret, falling back to SECRET_KEY if not set"""
    return settings.JWT_SECRET_KEY or settings.SECRET_KEY


def get_redis_url() -> str:
    """Get Redis URL with password if configured"""
    if settings.REDIS_PASSWORD:
        return f"redis://:{settings.REDIS_PASSWORD}@localhost:6379/0"
    return settings.REDIS_URL


def ensure_directories():
    """Ensure all required directories exist"""
    dirs = [
        settings.VIDEO_OUTPUT_DIR,
        settings.IMAGE_CACHE_DIR,
        settings.UPLOAD_DIR,
    ]
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
