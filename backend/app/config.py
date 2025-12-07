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
from pathlib import Path
import os


def _resolve_env_file() -> Optional[str]:
    """Resolve .env file path supporting both repo root and backend folder."""
    backend_dir = Path(__file__).resolve().parent.parent
    candidates = [
        backend_dir.parent / ".env",  # repository root
        backend_dir / ".env",         # backend/.env (legacy location)
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


ENV_FILE = _resolve_env_file()


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

    # OAuth Login Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_CLIENT_ID: Optional[str] = None
    FACEBOOK_CLIENT_SECRET: Optional[str] = None
    
    # Session Secret (for OAuth state)
    SESSION_SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_FOR_SESSIONS"

    # Ayrshare (unified social posting)
    AYRSHARE_API_KEY: Optional[str] = None

    # ==========================================================================
    # CORS & Security
    # ==========================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5500",  # Live Server
        "http://localhost:5500",  # Live Server
        "https://waitingthelongest.com",
        "https://www.waitingthelongest.com",
        "https://waitedthelongest.com",
        "https://www.waitedthelongest.com",
        "*", # Allow all for development
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
    # External API Keys
    # ==========================================================================
    RESCUEGROUPS_API_KEY: Optional[str] = None
    SERPAPI_KEY: Optional[str] = None

    # TheDogAPI (Dog breeds, images, knowledge library)
    # Rate limits: 100 req/60s, 200 burst, 10,000/month
    THEDOGAPI_KEY: Optional[str] = None
    THEDOGAPI_KEY_2: Optional[str] = None
    THEDOGAPI_KEY_3: Optional[str] = None
    THEDOGAPI_KEY_4: Optional[str] = None

    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    class Config:
        env_file = ENV_FILE or ".env"
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
