"""
Waiting The Longest™ - Configuration Schema
============================================
Environment configuration with validation.
"""

import os
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables.
    Environment variables are case-insensitive.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    
    # ==========================================================================
    # Application
    # ==========================================================================
    
    app_name: str = Field(
        default="Waiting The Longest™",
        description="Application name",
    )
    
    app_env: str = Field(
        default="development",
        description="Environment: development, staging, production",
    )
    
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    
    api_version: str = Field(
        default="v1",
        description="API version string",
    )
    
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for signing/encryption",
    )
    
    # ==========================================================================
    # Server
    # ==========================================================================
    
    host: str = Field(
        default="0.0.0.0",
        description="Server host to bind to",
    )
    
    port: int = Field(
        default=8000,
        description="Server port to listen on",
    )
    
    workers: int = Field(
        default=1,
        description="Number of worker processes",
    )
    
    # ==========================================================================
    # Database
    # ==========================================================================
    
    database_url: str = Field(
        default="sqlite:///./waitingthelongest.db",
        description="Database connection URL",
    )
    
    db_pool_size: int = Field(
        default=5,
        description="Database connection pool size",
    )
    
    db_max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections",
    )
    
    # ==========================================================================
    # Redis/Cache
    # ==========================================================================
    
    redis_url: Optional[str] = Field(
        default=None,
        description="Redis connection URL for caching",
    )
    
    cache_ttl: int = Field(
        default=300,
        description="Default cache TTL in seconds",
    )
    
    # ==========================================================================
    # Logging
    # ==========================================================================
    
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR",
    )
    
    log_format: str = Field(
        default="text",
        description="Log format: text, json",
    )
    
    log_file: Optional[str] = Field(
        default=None,
        description="Optional log file path",
    )
    
    # ==========================================================================
    # External Services
    # ==========================================================================
    
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking",
    )
    
    rescuegroups_api_key: Optional[str] = Field(
        default=None,
        description="RescueGroups API key",
    )
    
    petfinder_api_key: Optional[str] = Field(
        default=None,
        description="Petfinder API key",
    )
    
    petfinder_secret: Optional[str] = Field(
        default=None,
        description="Petfinder API secret",
    )
    
    # ==========================================================================
    # Email
    # ==========================================================================
    
    smtp_host: Optional[str] = Field(
        default=None,
        description="SMTP server hostname",
    )
    
    smtp_port: int = Field(
        default=587,
        description="SMTP server port",
    )
    
    smtp_user: Optional[str] = Field(
        default=None,
        description="SMTP username",
    )
    
    smtp_password: Optional[str] = Field(
        default=None,
        description="SMTP password",
    )
    
    smtp_from: str = Field(
        default="noreply@waitingthelongest.com",
        description="Default from email address",
    )
    
    # ==========================================================================
    # Monetization
    # ==========================================================================
    
    amazon_associate_tag: Optional[str] = Field(
        default=None,
        description="Amazon Associates tag",
    )
    
    chewy_affiliate_id: Optional[str] = Field(
        default=None,
        description="Chewy affiliate ID",
    )
    
    stripe_api_key: Optional[str] = Field(
        default=None,
        description="Stripe API key for donations",
    )
    
    # ==========================================================================
    # Rate Limiting
    # ==========================================================================
    
    rate_limit_per_minute: int = Field(
        default=60,
        description="API rate limit per minute per IP",
    )
    
    # ==========================================================================
    # CORS
    # ==========================================================================
    
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins",
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # ==========================================================================
    # Validators
    # ==========================================================================
    
    @field_validator("app_env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if v.lower() not in allowed:
            raise ValueError(f"app_env must be one of: {allowed}")
        return v.lower()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of: {allowed}")
        return v.upper()
    
    # ==========================================================================
    # Properties
    # ==========================================================================
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env == "development"
    
    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.app_env == "test"
    
    @property
    def use_redis(self) -> bool:
        """Check if Redis is configured."""
        return self.redis_url is not None
    
    @property
    def email_configured(self) -> bool:
        """Check if email is configured."""
        return self.smtp_host is not None


# =============================================================================
# Global Settings Instance
# =============================================================================

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    
    if _settings is None:
        _settings = Settings()
    
    return _settings


def override_settings(**kwargs) -> Settings:
    """Override settings for testing."""
    global _settings
    _settings = Settings(**kwargs)
    return _settings
