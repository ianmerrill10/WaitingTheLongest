"""
Waiting The Longest™ - Feature Flags
=====================================
Runtime feature flag management for gradual rollouts.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RolloutStrategy(Enum):
    """Strategy for feature rollout."""
    ALL = "all"  # Everyone gets the feature
    NONE = "none"  # No one gets the feature
    PERCENTAGE = "percentage"  # Random percentage of users
    USER_LIST = "user_list"  # Specific users only
    STAFF_ONLY = "staff_only"  # Internal users only


@dataclass
class FeatureFlag:
    """Definition of a feature flag."""
    key: str
    name: str
    description: str
    enabled: bool = True
    strategy: RolloutStrategy = RolloutStrategy.ALL
    percentage: float = 100.0  # For PERCENTAGE strategy
    user_list: Set[str] = field(default_factory=set)  # For USER_LIST strategy
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def is_enabled_for_user(self, user_id: Optional[str] = None) -> bool:
        """Check if feature is enabled for a specific user."""
        if not self.enabled:
            return False
        
        if self.strategy == RolloutStrategy.ALL:
            return True
        
        if self.strategy == RolloutStrategy.NONE:
            return False
        
        if self.strategy == RolloutStrategy.PERCENTAGE:
            if user_id is None:
                # For anonymous users, use a random check
                import random
                return random.random() * 100 < self.percentage
            else:
                # Use consistent hash for logged-in users
                import hashlib
                hash_val = int(hashlib.md5(f"{self.key}:{user_id}".encode()).hexdigest()[:8], 16)
                return (hash_val % 100) < self.percentage
        
        if self.strategy == RolloutStrategy.USER_LIST:
            return user_id in self.user_list
        
        if self.strategy == RolloutStrategy.STAFF_ONLY:
            # This would check against a staff list
            return user_id is not None and user_id.startswith("staff_")
        
        return False


class FeatureFlagManager:
    """
    Manage feature flags for the application.
    
    Supports:
    - Runtime flag toggling
    - Percentage-based rollouts
    - User-specific targeting
    - Environment-based defaults
    """
    
    def __init__(self):
        self.flags: Dict[str, FeatureFlag] = {}
        self._load_from_environment()
        self._register_defaults()
    
    def _load_from_environment(self) -> None:
        """Load flag overrides from environment variables."""
        # Format: FEATURE_FLAG_<KEY>=true|false
        for key, value in os.environ.items():
            if key.startswith("FEATURE_FLAG_"):
                flag_key = key[13:].lower()  # Remove prefix and lowercase
                self._env_overrides = getattr(self, "_env_overrides", {})
                self._env_overrides[flag_key] = value.lower() in ("true", "1", "yes")
    
    def _register_defaults(self) -> None:
        """Register default feature flags."""
        defaults = [
            FeatureFlag(
                key="newsletter",
                name="Newsletter Subscription",
                description="Enable newsletter subscription feature",
                enabled=True,
                strategy=RolloutStrategy.ALL,
            ),
            FeatureFlag(
                key="dark_mode",
                name="Dark Mode",
                description="Enable dark mode toggle",
                enabled=True,
                strategy=RolloutStrategy.ALL,
            ),
            FeatureFlag(
                key="favorites",
                name="Favorites",
                description="Enable favoriting animals",
                enabled=True,
                strategy=RolloutStrategy.ALL,
            ),
            FeatureFlag(
                key="share_buttons",
                name="Share Buttons",
                description="Show social share buttons",
                enabled=True,
                strategy=RolloutStrategy.ALL,
            ),
            FeatureFlag(
                key="affiliate_links",
                name="Affiliate Links",
                description="Show affiliate product recommendations",
                enabled=True,
                strategy=RolloutStrategy.ALL,
            ),
            FeatureFlag(
                key="success_stories",
                name="Success Stories",
                description="Show success stories section",
                enabled=True,
                strategy=RolloutStrategy.ALL,
            ),
            FeatureFlag(
                key="advanced_filters",
                name="Advanced Filters",
                description="Enable advanced search filters",
                enabled=True,
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=100.0,
            ),
            FeatureFlag(
                key="map_view",
                name="Map View",
                description="Enable map view of shelters",
                enabled=False,
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=0.0,
            ),
            FeatureFlag(
                key="notifications",
                name="Push Notifications",
                description="Enable push notifications",
                enabled=False,
                strategy=RolloutStrategy.STAFF_ONLY,
            ),
            FeatureFlag(
                key="donation_button",
                name="Donation Button",
                description="Show donation button",
                enabled=False,
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=50.0,
            ),
        ]
        
        for flag in defaults:
            self.register(flag)
    
    def register(self, flag: FeatureFlag) -> None:
        """Register a feature flag."""
        # Check for environment override
        env_overrides = getattr(self, "_env_overrides", {})
        if flag.key in env_overrides:
            flag.enabled = env_overrides[flag.key]
        
        self.flags[flag.key] = flag
    
    def is_enabled(
        self,
        flag_key: str,
        user_id: Optional[str] = None,
        default: bool = False,
    ) -> bool:
        """Check if a feature flag is enabled."""
        flag = self.flags.get(flag_key)
        
        if flag is None:
            logger.warning(f"Unknown feature flag: {flag_key}")
            return default
        
        return flag.is_enabled_for_user(user_id)
    
    def get_all_flags(self, user_id: Optional[str] = None) -> Dict[str, bool]:
        """Get status of all flags for a user."""
        return {
            key: flag.is_enabled_for_user(user_id)
            for key, flag in self.flags.items()
        }
    
    def get_flag_details(self, flag_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a flag."""
        flag = self.flags.get(flag_key)
        if flag is None:
            return None
        
        return {
            "key": flag.key,
            "name": flag.name,
            "description": flag.description,
            "enabled": flag.enabled,
            "strategy": flag.strategy.value,
            "percentage": flag.percentage if flag.strategy == RolloutStrategy.PERCENTAGE else None,
            "created_at": flag.created_at.isoformat(),
        }
    
    def update_flag(
        self,
        flag_key: str,
        enabled: Optional[bool] = None,
        strategy: Optional[RolloutStrategy] = None,
        percentage: Optional[float] = None,
    ) -> bool:
        """Update a feature flag at runtime."""
        flag = self.flags.get(flag_key)
        if flag is None:
            return False
        
        if enabled is not None:
            flag.enabled = enabled
        
        if strategy is not None:
            flag.strategy = strategy
        
        if percentage is not None:
            flag.percentage = max(0.0, min(100.0, percentage))
        
        logger.info(f"Updated feature flag: {flag_key}")
        return True


# =============================================================================
# Global Instance
# =============================================================================

_feature_flags: Optional[FeatureFlagManager] = None


def get_feature_flags() -> FeatureFlagManager:
    """Get the global feature flag manager."""
    global _feature_flags
    
    if _feature_flags is None:
        _feature_flags = FeatureFlagManager()
    
    return _feature_flags


def is_feature_enabled(flag_key: str, user_id: Optional[str] = None) -> bool:
    """Convenience function to check if a feature is enabled."""
    return get_feature_flags().is_enabled(flag_key, user_id)


def feature_flag(flag_key: str, default: bool = False):
    """Decorator to conditionally enable functionality based on feature flag."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            user_id = kwargs.get("user_id")
            if is_feature_enabled(flag_key, user_id):
                return func(*args, **kwargs)
            else:
                if default:
                    return func(*args, **kwargs)
                return None
        return wrapper
    return decorator
